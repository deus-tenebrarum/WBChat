import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import (
    Conversation,
    Message,
    MessageStatus,
    TypingIndicator,
    OnlineStatus,
    UserConversation,
)

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat messaging.
    Handles: sending/receiving messages, typing indicators, read receipts
    """

    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope['user']
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'

        # Reject anonymous users
        if not self.user.is_authenticated:
            await self.close()
            return

        # Verify user is part of conversation
        is_member = await self.check_conversation_membership()
        if not is_member:
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Update user's online status
        await self.update_online_status(online=True)

        # Notify others that user joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_join',
                'user_id': self.user.id,
                'username': self.user.username,
            }
        )

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        # Update user's online status
        await self.update_online_status(online=False)

        # Clear typing indicator
        await self.clear_typing_indicator()

        # Notify others that user left
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_leave',
                'user_id': self.user.id,
                'username': self.user.username,
            }
        )

    async def receive(self, text_data):
        """Receive message from WebSocket"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            elif message_type == 'read_receipt':
                await self.handle_read_receipt(data)
            elif message_type == 'edit_message':
                await self.handle_edit_message(data)
            elif message_type == 'delete_message':
                await self.handle_delete_message(data)
            elif message_type == 'reaction':
                await self.handle_reaction(data)

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON'
            }))

    async def handle_chat_message(self, data):
        """Handle incoming chat message"""
        content = data.get('message', '')
        reply_to_id = data.get('reply_to')

        if not content.strip():
            return

        # Save message to database
        message = await self.create_message(content, reply_to_id)

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': await self.message_to_dict(message),
            }
        )

        # Create message statuses for all participants
        await self.create_message_statuses(message)

    async def handle_typing(self, data):
        """Handle typing indicator"""
        is_typing = data.get('is_typing', False)

        if is_typing:
            await self.set_typing_indicator()
        else:
            await self.clear_typing_indicator()

        # Broadcast typing status to room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'username': self.user.username,
                'is_typing': is_typing,
            }
        )

    async def handle_read_receipt(self, data):
        """Handle read receipt for messages"""
        message_ids = data.get('message_ids', [])
        await self.mark_messages_as_read(message_ids)

        # Notify others about read receipts
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'read_receipt',
                'user_id': self.user.id,
                'message_ids': message_ids,
            }
        )

    async def handle_edit_message(self, data):
        """Handle message editing"""
        message_id = data.get('message_id')
        new_content = data.get('content', '')

        if not new_content.strip():
            return

        message = await self.edit_message(message_id, new_content)
        if message:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_edited',
                    'message': await self.message_to_dict(message),
                }
            )

    async def handle_delete_message(self, data):
        """Handle message deletion"""
        message_id = data.get('message_id')
        
        success = await self.delete_message(message_id)
        if success:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_deleted',
                    'message_id': message_id,
                    'user_id': self.user.id,
                }
            )

    async def handle_reaction(self, data):
        """Handle message reactions"""
        message_id = data.get('message_id')
        emoji = data.get('emoji')
        action = data.get('action', 'add')  # 'add' or 'remove'

        if action == 'add':
            await self.add_reaction(message_id, emoji)
        else:
            await self.remove_reaction(message_id, emoji)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'message_reaction',
                'message_id': message_id,
                'user_id': self.user.id,
                'emoji': emoji,
                'action': action,
            }
        )

    # WebSocket message handlers (called by group_send)
    async def chat_message(self, event):
        """Send chat message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
        }))

    async def typing_indicator(self, event):
        """Send typing indicator to WebSocket"""
        # Don't send own typing indicator back
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'username': event['username'],
                'is_typing': event['is_typing'],
            }))

    async def read_receipt(self, event):
        """Send read receipt to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'read_receipt',
            'user_id': event['user_id'],
            'message_ids': event['message_ids'],
        }))

    async def message_edited(self, event):
        """Send edited message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'message_edited',
            'message': event['message'],
        }))

    async def message_deleted(self, event):
        """Send message deletion notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'message_deleted',
            'message_id': event['message_id'],
            'user_id': event['user_id'],
        }))

    async def message_reaction(self, event):
        """Send reaction update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'reaction',
            'message_id': event['message_id'],
            'user_id': event['user_id'],
            'emoji': event['emoji'],
            'action': event['action'],
        }))

    async def user_join(self, event):
        """Notify about user joining"""
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user_join',
                'user_id': event['user_id'],
                'username': event['username'],
            }))

    async def user_leave(self, event):
        """Notify about user leaving"""
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user_leave',
                'user_id': event['user_id'],
                'username': event['username'],
            }))

    # Database operations
    @database_sync_to_async
    def check_conversation_membership(self):
        """Check if user is a member of the conversation"""
        return UserConversation.objects.filter(
            user=self.user,
            conversation_id=self.conversation_id,
            left_at__isnull=True
        ).exists()

    @database_sync_to_async
    def create_message(self, content, reply_to_id=None):
        """Create a new message in the database"""
        message = Message.objects.create(
            conversation_id=self.conversation_id,
            author=self.user,
            content=content,
            reply_to_id=reply_to_id,
        )
        # Update conversation's updated_at
        Conversation.objects.filter(id=self.conversation_id).update(
            updated_at=timezone.now()
        )
        return message

    @database_sync_to_async
    def edit_message(self, message_id, new_content):
        """Edit an existing message"""
        try:
            message = Message.objects.get(
                id=message_id,
                author=self.user,
                conversation_id=self.conversation_id,
                is_deleted=False
            )
            message.edit(new_content)
            return message
        except Message.DoesNotExist:
            return None

    @database_sync_to_async
    def delete_message(self, message_id):
        """Soft delete a message"""
        try:
            message = Message.objects.get(
                id=message_id,
                author=self.user,
                conversation_id=self.conversation_id
            )
            message.soft_delete()
            return True
        except Message.DoesNotExist:
            return False

    @database_sync_to_async
    def create_message_statuses(self, message):
        """Create message status entries for all conversation participants"""
        participants = UserConversation.objects.filter(
            conversation_id=self.conversation_id,
            left_at__isnull=True
        ).exclude(user=self.user)

        statuses = [
            MessageStatus(
                message=message,
                user=uc.user,
                status='sent'
            )
            for uc in participants
        ]
        MessageStatus.objects.bulk_create(statuses)

    @database_sync_to_async
    def mark_messages_as_read(self, message_ids):
        """Mark multiple messages as read"""
        MessageStatus.objects.filter(
            message_id__in=message_ids,
            user=self.user
        ).update(
            status='read',
            read_at=timezone.now()
        )

        # Update last_read_at for user conversation
        UserConversation.objects.filter(
            user=self.user,
            conversation_id=self.conversation_id
        ).update(last_read_at=timezone.now())

    @database_sync_to_async
    def add_reaction(self, message_id, emoji):
        """Add a reaction to a message"""
        from .models import Reaction
        Reaction.objects.get_or_create(
            message_id=message_id,
            user=self.user,
            emoji=emoji
        )

    @database_sync_to_async
    def remove_reaction(self, message_id, emoji):
        """Remove a reaction from a message"""
        from .models import Reaction
        Reaction.objects.filter(
            message_id=message_id,
            user=self.user,
            emoji=emoji
        ).delete()

    @database_sync_to_async
    def set_typing_indicator(self):
        """Set typing indicator for user"""
        TypingIndicator.objects.update_or_create(
            conversation_id=self.conversation_id,
            user=self.user,
            defaults={'started_at': timezone.now()}
        )

    @database_sync_to_async
    def clear_typing_indicator(self):
        """Clear typing indicator for user"""
        TypingIndicator.objects.filter(
            conversation_id=self.conversation_id,
            user=self.user
        ).delete()

    @database_sync_to_async
    def update_online_status(self, online=True):
        """Update user's online status"""
        status, created = OnlineStatus.objects.get_or_create(
            user=self.user
        )
        if online:
            status.go_online()
            status.update_activity(conversation_id=self.conversation_id)
        else:
            status.go_offline()

    @database_sync_to_async
    def message_to_dict(self, message):
        """Convert message object to dictionary"""
        return {
            'id': message.id,
            'author_id': message.author.id if message.author else None,
            'author_username': message.author.username if message.author else 'System',
            'content': message.content,
            'type': message.type,
            'created_at': message.created_at.isoformat(),
            'is_edited': message.is_edited,
            'edited_at': message.edited_at.isoformat() if message.edited_at else None,
            'reply_to_id': message.reply_to_id,
        }


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time notifications.
    Handles: new message notifications, mentions, system notifications
    """

    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope['user']

        # Reject anonymous users
        if not self.user.is_authenticated:
            await self.close()
            return

        self.user_notification_group = f'notifications_{self.user.id}'

        # Join user's notification group
        await self.channel_layer.group_add(
            self.user_notification_group,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave notification group
        await self.channel_layer.group_discard(
            self.user_notification_group,
            self.channel_name
        )

    async def receive(self, text_data):
        """Receive message from WebSocket"""
        # Could handle notification preferences updates here
        pass

    async def notification(self, event):
        """Send notification to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification'],
        }))

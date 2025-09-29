import React from 'react';
import ChatMessage, {MessageType} from "@/types/Chat";
import './RoomChatSection.scss';

interface Props {
  chatMessages: ChatMessage[];
}

const RoomChatSection: React.FC<Props> = ({chatMessages}) => {
  // Get room id from URL/router

  // use a webhook (make sure to close the webhook on unmount)

  const chats: ChatMessage[] = [
    new ChatMessage({
      gameId: 1,
      senderId: 1,
      messageText: "hi!",
      messageId: 1,
      messageType: MessageType.GENERAL,
      timestamp: new Date(),
    }),
    new ChatMessage({
      gameId: 1,
      senderId: 1,
      messageText: "How are you?",
      messageId: 2,
      messageType: MessageType.GENERAL,
      timestamp: new Date(),
    }),
  ];

  // TODO: order by time
  // TODO: render only visible chat messages.

  return (
    <section className="chat">
      {/* TODO header */}
      <ul>
        {chats.map((chatMessage) => (
          <li key={chatMessage.messageId}>
            {chatMessage.messageText}
          </li>
        ))}
      </ul>
    </section>
  );
};

export default RoomChatSection;

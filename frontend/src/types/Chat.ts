export enum MessageType {
  HINT = "HINT",
  GUESS = "GUESS",
  SYSTEM = "SYSTEM",
  GENERAL = "GENERAL",
}


interface ChatMessageArgs {
  messageId: number;
  gameId: number;
  senderId?: number | null;
  messageText: string;
  messageType: MessageType;
  timestamp: Date | string;
}

export class ChatMessage {
  messageId: number;
  gameId: number;
  senderId: number | null;
  messageText: string;
  messageType: MessageType;
  timestamp: Date;

  constructor({
                messageId,
                gameId,
                senderId = null,
                messageText,
                messageType,
                timestamp,
              }: ChatMessageArgs) {
    this.messageId = messageId;
    this.gameId = gameId;
    this.senderId = senderId || null;
    this.messageText = messageText;
    this.messageType = messageType;
    this.timestamp = new Date(timestamp);
  }
}


export default ChatMessage;

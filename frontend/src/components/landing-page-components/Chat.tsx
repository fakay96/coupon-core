import { Button } from "@/components/ui/button";
import { categoriesApiQuery } from "@/queries/geo-discount-queries";
import { categoriesT, Message } from "@/types";
import React, {
  useState,
  useRef,
  useEffect,
  KeyboardEvent,
  ChangeEvent,
  SetStateAction,
  Dispatch,
} from "react";
import { BsFillSendFill } from "react-icons/bs";
import { Link } from "react-router-dom";
import ChatMessage from "./ChatMessage";
import { geodiscountApiMutation } from "@/queries/auth-queries";
import { Loader } from "lucide-react";

interface ChatAppProps {
  inputValue: string;
  setInputValue: Dispatch<SetStateAction<string>>;
  messages?: Message[];
  setMessages: Dispatch<SetStateAction<Message[]>>;
  initialGreeting?: string;
  onSendMessage?: (message: string) => Promise<string>;
}

/**
 * ChatApp - A component that renders a chat interface similar to ChatGPT
 *
 * Features:
 * - Initial centered input field that moves to bottom after first message
 * - Dynamic message display with user messages on right, assistant on left
 * - Auto-expanding text input as user types
 * - Proper message history management
 */
const Chat: React.FC<ChatAppProps> = ({
  inputValue,
  setInputValue,
  messages,
  setMessages,
}) => {
  const [isFirstMessage, setIsFirstMessage] = useState<boolean>(true);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const { data: categories } = categoriesApiQuery();
  const { mutateAsync: updateUserProfile } = geodiscountApiMutation();

  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const chatWrapperRef = useRef<HTMLDivElement>(null);
  const chatAreaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Auto-resize textarea as content grows
  useEffect(() => {
    if (textareaRef.current) {
      adjustTextareaHeight();
    }
  }, [inputValue]);

  /**
   * Adjusts the height of the textarea based on content
   * Maintains a minimum height but allows expansion as needed
   */
  const adjustTextareaHeight = (): void => {
    const textarea = textareaRef.current;
    const chatWrapper = chatWrapperRef.current;
    const chatArea = chatAreaRef.current;
    if (!textarea || !chatWrapper || !chatArea) return;

    textarea.style.height = "auto";
    const newHeight = Math.max(textarea.scrollHeight, 5);
    textarea.style.height = `${newHeight}px`;

    // Dynamically toggle class based on height
    if (newHeight > 60) {
      chatWrapper.classList.remove("rounded-full");
      chatWrapper.classList.add("rounded-md"); // or any other rounded level
    } else {
      chatWrapper.classList.remove("rounded-md");
      chatWrapper.classList.add("rounded-full");
    }

    if (chatArea?.offsetHeight >= 30) {
      chatArea.classList.add("my-32");
    }
  };

  /**
   * Handles input change and adjusts textarea height
   */
  const handleInputChange = (e: ChangeEvent<HTMLTextAreaElement>): void => {
    setInputValue(e.target.value);
  };

  /**
   * Scrolls the chat to the most recent message
   */
  const scrollToBottom = (): void => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  /**
   * Generates a unique ID for messages
   */
  const generateId = (): string => {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  };
  useEffect(() => {
    if (!isLoading && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isLoading]);
  /**
   * Handles form submission and message sending
   */
  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();

    if (!inputValue.trim()) return;

    // Create user message
    const userMessage: Message = {
      id: generateId(),
      content: inputValue.trim(),
      sender: "user",
      timestamp: new Date(),
    };

    // Update state to reflect user message
    setMessages((prevMessages) => [...prevMessages, userMessage]);
    setInputValue("");
    setIsFirstMessage(false);
    setIsLoading(true);

    try {
      // Get response from assistant (using prop callback)
      const update = await updateUserProfile({ query: inputValue });

      // Create assistant message from response
      const assistantMessage: Message = {
        id: generateId(),
        content: update?.message,
        sender: "dishpal",
        timestamp: new Date(),
      };

      // Update message history with assistant response
      setMessages((prevMessages) => [...prevMessages, assistantMessage]);
    } catch (error) {
      console.error("Error getting assistant response:", error);

      // Add error message if response fails
      const errorMessage: Message = {
        id: generateId(),
        content: "Sorry, I encountered an error processing your request.",
        sender: "dishpal",
        timestamp: new Date(),
      };

      setMessages((prevMessages) => [...prevMessages, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Handles keyboard shortcuts for submission
   */
  const handleKeyDown = async (
    e: KeyboardEvent<HTMLTextAreaElement>
  ): Promise<void> => {
    // Submit on Enter without Shift key
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      await handleSubmit(e);
    }
  };

  return (
    <div className="chat-container">
      <div ref={chatAreaRef} className="max-w-3xl mx-auto">
        {messages?.map((message) => (
          <ChatMessage
            key={message.id}
            content={message.content}
            sender={message.sender}
          />
        ))}

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex gap-2">
            <Loader className="animate-spin" /> Dishpal Ai is working on your
            request.
          </div>
        )}

        {/* Auto-scroll anchor */}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div
        className={`space-y-4 z-50 backdrop-blur-md ${
          isFirstMessage
            ? "centered"
            : "fixed bottom-0 left-1/2 transform -translate-x-1/2 w-full p-4 sm:px-6"
        }`}
      >
        <form onSubmit={handleSubmit}>
          <div
            ref={chatWrapperRef}
            className="rounded-full px-1 py-1 max-w-sm sm:max-w-screen-sm mx-auto flex items-center gap-2 border-[1px] border-vividOrange "
          >
            <img
              alt="dispal"
              src="/images/smilling.svg"
              className="w-5 sm:w-10 h-auto"
            />

            <textarea
              ref={textareaRef}
              value={inputValue}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="Type your message here..."
              rows={1}
              className="bg-transparent w-full outline-none focus:outline-none max-sm:text-[12px] resize-none"
              disabled={isLoading}
              autoFocus
            />
            <Button
              type="submit"
              disabled={!inputValue.trim() || isLoading}
              className="ml-auto rounded-full py-0 p-1.5 h-auto sm:h-11 sm:p-4 bg-vividOrange"
            >
              <span className="hidden sm:flex">Find Deals </span>{" "}
              <BsFillSendFill className="!size-3 sm:size-4" />
            </Button>
          </div>
        </form>
        <div className="flex flex-wrap max-sm:gap-2 gap-4 mx-auto max-w-screen-lg items-center justify-center">
          {categories?.map(({ id, image, name }: categoriesT) => (
            <Link
              to={`/dashboard/category?category=${name}`}
              key={id}
              className="border-[1px] flex max-sm:gap-2 gap-4 py-1 px-4 rounded-full border-gray-300 hover:cursor-pointer items-center justify-center"
            >
              <img src={image} className="max-sm:size-3" alt={image} />
              <span className="max-sm:text-[10px]">{name}</span>{" "}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Chat;

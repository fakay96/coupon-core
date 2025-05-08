import { TypeAnimation } from "react-type-animation";
import React from "react";

type Props = {
  content: string;
  sender: "user" | "dishpal";
};

const ChatMessage: React.FC<Props> = ({ content, sender }) => {

  return (
    <div
      className={`w-fit my-4 p-2 px-4 ${
        sender === "user" ? "ml-auto bg-red-50 rounded-2xl" : "mr-auto"
      }`}
    >
      <div className="message-content">
        <div className="message-text whitespace-pre-wrap">
          {sender === "user" ? (
            content
          ) : (
            <TypeAnimation
              sequence={[content]}
              wrapper="span"
              speed={50}
              cursor={false}
              style={{ fontSize: "1em", display: "inline-block" }}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatMessage;

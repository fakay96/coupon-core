import SearchInputNavbar from "@/components/globals/searchInputNavbar";
import { useState } from "react";
import Chat from "@/components/landing-page-components/Chat";
import { isEmpty } from "lodash";
import { Message } from "@/types";

// Define message type

const Homepage = () => {
  const [inputValue, setInputValue] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);
  return (
    <div className="">
      <div className="bg-bg3xl bg-cover">
        <div className="flex flex-col h-full min-h-screen max-w-screen-xl mx-auto px-4 sm:px-8">
          <div className="relative">
            <div className="absolute left-0 top-0 w-full">
              <SearchInputNavbar />
            </div>
          </div>
          <>
            <div className="flex-1 flex flex-col justify-center ">
              {isEmpty(messages) && (
                <div className=" flex flex-col text-center mx-auto space-y-4 sm:space-y-8 mb-4">
                  <div className="max-sm:py-4 space-y-2">
                    <h1 className="font-syne capitalize font-bold text-3xl sm:text-4xl text-vividOrange">
                      What can i help you find?
                    </h1>
                    <p className="font-syne capitalize">
                      Powered by AI to save you time and money
                    </p>
                  </div>
                </div>
              )}
              <div className="max-sm:mt-2 space-y-8 ">
                <Chat
                  inputValue={inputValue}
                  setInputValue={setInputValue}
                  messages={messages}
                  setMessages={setMessages}
                />
              </div>
            </div>
          </>
        </div>
      </div>
    </div>
  );
};

export default Homepage;

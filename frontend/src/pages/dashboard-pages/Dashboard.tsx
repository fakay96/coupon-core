import SearchInputNavbar from "@/components/globals/searchInputNavbar";
import Chat from "@/components/landing-page-components/Chat";
import { imgGrid } from "@/constants";
import { Message } from "@/types";
import { isEmpty } from "lodash";
import { useState } from "react";
import { Link } from "react-router-dom";

const DashboardPage = () => {
  const [inputValue, setInputValue] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);
  return (
    <div className="">
      <div className="bg-bg3xl bg-cover">
        <div className="flex flex-col h-full min-h-screen max-w-screen-xl mx-auto px-4 sm:px-8 ">
          <SearchInputNavbar link={"/"} />
          <>
            <div className="flex-1 flex-col flex items-center justify-center py-12">
              {isEmpty(messages) && (
                <div className="max-w-xl text-center mx-auto flex flex-col space-y-4 mb-8">
                  <div className="">
                    <h1 className="font-syne capitalize font-bold text-2xl sm:text-4xl text-vividOrange max-sm:max-w-sm mx-auto">
                      Search for the deals that matter to you
                    </h1>
                    <p className="font-syne capitalize">Follow these steps</p>
                  </div>
                  <div className="max-sm:max-w-sm mx-auto">
                    <div className="grid grid-cols-2 sm:grid-cols-4  justify-center items-center gap-4">
                      {imgGrid.map(
                        ({ img, topTitle, bottomTitle, href }, index) => (
                          <Link
                            to={href}
                            key={index}
                            className="relative h-36 rounded-3xl overflow-hidden "
                          >
                            <img src={img} alt="" />
                            <div className="absolute bottom-0 pb-2 bg-gradient-to-t from-black to-transparent w-full pl-4">
                              <p className="text-white font-syne text-start font-bold">
                                {topTitle}
                              </p>
                              <p className="text-white font-syne text-start font-bold -mt-2">
                                {bottomTitle}
                              </p>
                            </div>
                          </Link>
                        )
                      )}
                    </div>
                  </div>
                </div>
              )}
              <div className="max-sm:mt-2 space-y-8 w-full max-w-2xl">
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

export default DashboardPage;



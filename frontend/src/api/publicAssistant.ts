import { api } from "./client";

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

export async function askTisaxAssistant(message: string, history: ChatTurn[]): Promise<string> {
  const { data } = await api.post<{ reply: string }>("/api/v1/public/tisax-assistant", {
    message,
    history,
  });
  return data.reply;
}
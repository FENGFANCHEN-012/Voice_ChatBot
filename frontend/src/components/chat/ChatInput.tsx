export function ChatInput() {
  return (
    <div className="border-t p-4 flex gap-2">
      <input
        type="text"
        placeholder="Type a message..."
        className="flex-1 border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
      />
    </div>
  );
}

interface Props {
  message: string;
  type: "success" | "error" | "info";
}

export function Toast({ message, type }: Props) {
  const colors = {
    success: "bg-green-500",
    error: "bg-red-500",
    info: "bg-blue-500",
  };
  return (
    <div className={`fixed bottom-4 right-4 ${colors[type]} text-white px-4 py-2 rounded-lg shadow-lg`}>
      {message}
    </div>
  );
}

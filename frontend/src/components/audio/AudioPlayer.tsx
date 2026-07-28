interface Props {
  audioUrl: string | null;
}

export function AudioPlayer({ audioUrl }: Props) {
  if (!audioUrl) return null;
  return <audio src={audioUrl} controls className="w-full mt-2" />;
}

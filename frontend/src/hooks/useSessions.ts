import { useState, useEffect, useCallback } from "react";
import type { Session } from "../types";
import { createSession, listSessions, deleteSession } from "../services/api";

export function useSessions() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentId, setCurrentId] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    const { data } = await listSessions();
    setSessions(data);
  }, []);

  const create = useCallback(async () => {
    const { data } = await createSession();
    setSessions((prev) => [...prev, data]);
    setCurrentId(data.session_id);
    return data;
  }, []);

  const remove = useCallback(async (id: string) => {
    await deleteSession(id);
    setSessions((prev) => prev.filter((s) => s.session_id !== id));
    if (currentId === id) setCurrentId(null);
  }, [currentId]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { sessions, currentId, setCurrentId, create, remove };
}

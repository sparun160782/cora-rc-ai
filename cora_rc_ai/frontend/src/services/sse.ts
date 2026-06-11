import { useChatStore } from '../store/chatStore';
import { v4 as uuidv4 } from 'uuid';
import { API_BASE_URL } from './api';

export const streamAgentResponse = async (
  message: string,
  sessionId: string | null,
  jurisdiction?: string
) => {
  const store = useChatStore.getState();
  const activePersona = store.activePersona;

  store.addMessage({
    id: uuidv4(),
    role: 'user',
    content: message,
    timestamp: new Date().toISOString(),
  });

  const agentMessageId = uuidv4();
  store.addMessage({
    id: agentMessageId,
    role: 'agent',
    content: '',
    timestamp: new Date().toISOString(),
    isStreaming: true,
  });

  try {
    const response = await fetch(`${API_BASE_URL}/regulations/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question: message,
        session_id: sessionId,
        jurisdiction: jurisdiction || 'GLOBAL',
        user_id: 'default_user',
        persona: activePersona,
        stream: true,
      }),
    });

    if (!response.ok) {
      throw new Error('Network response was not ok');
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    let fullContent = '';
    let doneReceived = false;
    const fallbackMessage =
      'I could not generate a final response from the model. Please try again.';

    if (reader) {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        let eventSeparatorIndex = buffer.indexOf('\n\n');
        while (eventSeparatorIndex !== -1) {
          const rawEvent = buffer.slice(0, eventSeparatorIndex);
          buffer = buffer.slice(eventSeparatorIndex + 2);

          const lines = rawEvent.split('\n');
          for (const line of lines) {
            if (!line.startsWith('data:')) {
              continue;
            }

            const payload = line.slice(5).trimStart();
            if (!payload) {
              continue;
            }

            try {
              const data = JSON.parse(payload);

              if (data.type === 'session_id' && !store.sessionId) {
                store.setSessionId(data.session_id);
              } else if (data.type === 'token') {
                fullContent += data.content ?? '';
                store.updateLastMessage(fullContent);
              } else if (data.type === 'done') {
                doneReceived = true;
                store.updateLastMessage(fullContent, true);
                await store.fetchSessions();
              } else if (data.type === 'error') {
                doneReceived = true;
                store.updateLastMessage(`Error: ${data.message}`, true);
              }
            } catch (e) {
              console.error('Error parsing SSE chunk:', e, payload);
            }
          }

          eventSeparatorIndex = buffer.indexOf('\n\n');
        }
      }
    }

    if (buffer.trim()) {
      const lines = buffer.split('\n');
      for (const line of lines) {
        if (!line.startsWith('data:')) {
          continue;
        }

        const payload = line.slice(5).trimStart();
        if (!payload) {
          continue;
        }

        try {
          const data = JSON.parse(payload);

          if (data.type === 'session_id' && !store.sessionId) {
            store.setSessionId(data.session_id);
          } else if (data.type === 'token') {
            fullContent += data.content ?? '';
            store.updateLastMessage(fullContent);
          } else if (data.type === 'done') {
            doneReceived = true;
            store.updateLastMessage(fullContent, true);
            await store.fetchSessions();
          } else if (data.type === 'error') {
            doneReceived = true;
            store.updateLastMessage(`Error: ${data.message}`, true);
          }
        } catch (e) {
          console.error('Error parsing final SSE chunk:', e, payload);
        }
      }
    }

    // Final safety net: if stream closed without explicit done/error, finalize message.
    if (!doneReceived) {
      store.updateLastMessage(fullContent || fallbackMessage, true);
      await store.fetchSessions();
    }
  } catch (error) {
    console.error('Streaming error:', error);
    store.updateLastMessage('Sorry, there was an error processing your request.', true);
  }
};
import { CheckCircle2 } from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

interface Toast {
  id: number;
  message: string;
  undo?: () => void;
}

interface ToastApi {
  /** Show a short message, with an Undo button when `undo` is given. */
  show: (message: string, undo?: () => void) => void;
}

const ToastContext = createContext<ToastApi | null>(null);
const SHOW_MS = 5000;

/** Toasts for optimistic actions: bottom-centre, announced politely, each with an optional Undo. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const show = useCallback(
    (message: string, undo?: () => void) => {
      const id = nextId.current++;
      setToasts((current) => [...current.slice(-2), { id, message, undo }]);
      window.setTimeout(() => dismiss(id), SHOW_MS);
    },
    [dismiss],
  );

  const api = useMemo(() => ({ show }), [show]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed inset-x-0 bottom-20 z-[60] flex flex-col items-center gap-2 px-4 md:bottom-6"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className="toast pointer-events-auto flex min-h-12 w-full max-w-md items-center gap-3 rounded-xl bg-ink py-2 pr-2 pl-4 text-[15px] text-white shadow-lift"
          >
            <CheckCircle2 className="size-[18px] shrink-0 text-primary" aria-hidden />
            <span className="flex-1">{toast.message}</span>
            {toast.undo && (
              <button
                type="button"
                className="h-9 rounded-lg px-3 font-semibold text-primary transition-colors hover:bg-white/10"
                onClick={() => {
                  toast.undo?.();
                  dismiss(toast.id);
                }}
              >
                Undo
              </button>
            )}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

/** The toast API. */
export function useToast(): ToastApi {
  const api = useContext(ToastContext);
  if (!api) {
    throw new Error("useToast needs a ToastProvider.");
  }
  return api;
}

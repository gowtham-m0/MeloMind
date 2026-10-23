import { useId, useState } from "react";

import { Button } from "@/shared/ui/button";

interface PromptEditorProps {
  prompt: string;
  saving: boolean;
  onSave: (text: string) => void;
}

/** The conversation prompt under an item, which the caregiver can reword before approving. */
export function PromptEditor({ prompt, saving, onSave }: PromptEditorProps) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(prompt);
  const id = useId();

  if (!editing) {
    return (
      <div className="flex flex-wrap items-start gap-3">
        <p className="flex-1 italic">“{prompt}”</p>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            setText(prompt);
            setEditing(true);
          }}
        >
          Edit prompt
        </Button>
      </div>
    );
  }
  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        onSave(text);
        setEditing(false);
      }}
    >
      <label htmlFor={id} className="font-semibold">
        Conversation prompt
      </label>
      <textarea
        id={id}
        value={text}
        maxLength={300}
        rows={2}
        onChange={(event) => setText(event.target.value)}
        className="rounded-md border-2 border-input bg-background p-3 text-lg"
      />
      <p className="text-base text-muted-foreground">
        Keep it open and gentle, like “What does this bring to mind?”, rather than a memory test.
      </p>
      <div className="flex gap-2">
        <Button type="submit" size="sm" disabled={saving}>
          Save prompt
        </Button>
        <Button type="button" variant="outline" size="sm" onClick={() => setEditing(false)}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

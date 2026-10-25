import { apiRequest, apiUpload } from "./client";
import type { components } from "./schema";

type Schemas = components["schemas"];

/** An entry with its confirmed links and open suggestions. */
export type JournalEntry = Schemas["JournalEntryOut"];
/** A link from an entry to an item or place. */
export type JournalLink = Schemas["JournalLinkOut"];
/** What a link points to. */
export type JournalTarget = Schemas["JournalTargetOut"];
/** A new entry. */
export type JournalEntryCreate = Schemas["JournalEntryCreate"];
/** Fields to change on an entry. */
export type JournalEntryUpdate = Schemas["JournalEntryUpdate"];

const journalUrl = (profileId: string) => `/api/v1/profiles/${profileId}/journal`;

/** GET /profiles/{id}/journal: entries newest first (the last 60 days by default). */
export function listEntries(profileId: string): Promise<JournalEntry[]> {
  return apiRequest<JournalEntry[]>("GET", journalUrl(profileId));
}

/** GET /profiles/{id}/journal/{entryId}. */
export function getEntry(profileId: string, entryId: string): Promise<JournalEntry> {
  return apiRequest<JournalEntry>("GET", `${journalUrl(profileId)}/${entryId}`);
}

/** POST /profiles/{id}/journal: saves the entry and starts a link run (`link_run_id`). */
export function createEntry(profileId: string, body: JournalEntryCreate): Promise<JournalEntry> {
  return apiRequest<JournalEntry>("POST", journalUrl(profileId), body);
}

/** PATCH /profiles/{id}/journal/{entryId}: new text starts a new link run. */
export function updateEntry(
  profileId: string,
  entryId: string,
  body: JournalEntryUpdate,
): Promise<JournalEntry> {
  return apiRequest<JournalEntry>("PATCH", `${journalUrl(profileId)}/${entryId}`, body);
}

/** DELETE /profiles/{id}/journal/{entryId}: its links and their signals go too. */
export function deleteEntry(profileId: string, entryId: string): Promise<void> {
  return apiRequest<void>("DELETE", `${journalUrl(profileId)}/${entryId}`);
}

/** PATCH /profiles/{id}/journal/links/{linkId}: confirm or reject one suggestion. */
export function decideLink(
  profileId: string,
  linkId: string,
  status: "confirmed" | "rejected",
): Promise<JournalLink> {
  return apiRequest<JournalLink>("PATCH", `${journalUrl(profileId)}/links/${linkId}`, { status });
}

/** POST /profiles/{id}/journal/{entryId}/links/confirm-all. */
export function confirmAll(profileId: string, entryId: string): Promise<JournalEntry> {
  return apiRequest<JournalEntry>("POST", `${journalUrl(profileId)}/${entryId}/links/confirm-all`);
}

/** POST /profiles/{id}/journal/{entryId}/links/suggest: ask the agent again. */
export function suggestLinks(profileId: string, entryId: string): Promise<JournalEntry> {
  return apiRequest<JournalEntry>("POST", `${journalUrl(profileId)}/${entryId}/links/suggest`);
}

/** POST /profiles/{id}/journal/transcribe: a voice note to text. The audio isn't kept. */
export function transcribe(profileId: string, audio: Blob): Promise<{ text: string }> {
  return apiUpload<{ text: string }>(`${journalUrl(profileId)}/transcribe`, audio);
}

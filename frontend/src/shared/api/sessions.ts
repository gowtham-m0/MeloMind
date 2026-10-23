import { apiRequest } from "./client";
import type { components } from "./schema";

type Schemas = components["schemas"];

/** A session or warm-up set, with its items in play order. */
export type SessionDraft = Schemas["SessionDraftOut"];
/** One item of a session. A book has no media: it's a conversation slot. */
export type SessionItem = Schemas["SessionItemOut"];
/** A playable video, or demo stand-in media. */
export type Media = Schemas["MediaOut"];
/** planning, draft, approved, in_progress, completed or failed. */
export type SessionStatus = Schemas["SessionStatus"];
/** A session in the history list. */
export type SessionSummary = Schemas["SessionSummaryOut"];
/** What to plan: the mode and the length. */
export type PlanRequest = Schemas["PlanRequestIn"];
/** Changes to a draft: removals, a new order and edited prompts. */
export type ItemsPatch = Schemas["ItemsPatch"];
/** sang_along, smiled, calm, neutral, upset or rejected. */
export type Reaction = Schemas["Reaction"];
/** Whether feedback counted, and what it changes. */
export type FeedbackResult = Schemas["FeedbackOut"];
/** An agent run and its plain-English log. */
export type AgentRun = Schemas["AgentRunOut"];
/** One entry in the agent log. */
export type AgentStep = Schemas["AgentStepOut"];

const API = "/api/v1";

/** POST /profiles/{id}/sessions/plan: starts planning in the background. */
export function planSession(profileId: string, body: PlanRequest): Promise<SessionDraft> {
  return apiRequest<SessionDraft>("POST", `${API}/profiles/${profileId}/sessions/plan`, body);
}

/** GET /sessions/{id}. */
export function getSession(id: string): Promise<SessionDraft> {
  return apiRequest<SessionDraft>("GET", `${API}/sessions/${id}`);
}

/** GET /profiles/{id}/history: sessions and warm-up sets, newest first. */
export function getHistory(profileId: string): Promise<SessionSummary[]> {
  return apiRequest<SessionSummary[]>("GET", `${API}/profiles/${profileId}/history`);
}

/** PATCH /sessions/{id}/items: only while the session is a draft. */
export function editItems(id: string, body: ItemsPatch): Promise<SessionDraft> {
  return apiRequest<SessionDraft>("PATCH", `${API}/sessions/${id}/items`, body);
}

/** The status changes the caregiver makes. */
export type SessionAction = "approve" | "start" | "complete";

/** POST /sessions/{id}/approve, /start or /complete. */
export function changeSession(id: string, action: SessionAction): Promise<SessionDraft> {
  return apiRequest<SessionDraft>("POST", `${API}/sessions/${id}/${action}`);
}

/** POST /sessions/{id}/items/{itemId}/feedback: the caregiver's reaction. */
export function reactToItem(
  sessionId: string,
  itemId: string,
  reaction: Reaction,
): Promise<FeedbackResult> {
  return apiRequest<FeedbackResult>(
    "POST",
    `${API}/sessions/${sessionId}/items/${itemId}/feedback`,
    { reaction },
  );
}

/** GET /agent-runs/{id}: the log, polled while the agent works. */
export function getAgentRun(id: string): Promise<AgentRun> {
  return apiRequest<AgentRun>("GET", `${API}/agent-runs/${id}`);
}

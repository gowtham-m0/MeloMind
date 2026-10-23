import { apiRequest } from "./client";
import type { components } from "./schema";

type Schemas = components["schemas"];

/** A profile with its favourites. */
export type Profile = Schemas["ProfileOut"];
/** Fields for a new profile: only the display name and birth year are required. */
export type ProfileCreate = Schemas["ProfileCreate"];
/** Any profile fields to change. */
export type ProfileUpdate = Schemas["ProfileUpdate"];
/** A saved favourite. */
export type Favourite = Schemas["FavouriteOut"];
/** A favourite to save. Send `entity_id` when it came from a taste-search match. */
export type FavouriteCreate = Schemas["FavouriteCreate"];
/** artist, song, movie, tv_show or book. */
export type FavouriteKind = Schemas["FavouriteKind"];

const PROFILES = "/api/v1/profiles";

/** GET /profiles: the signed-in user's profiles. */
export function listProfiles(): Promise<Profile[]> {
  return apiRequest<Profile[]>("GET", PROFILES);
}

/** GET /profiles/{id}. */
export function getProfile(id: string): Promise<Profile> {
  return apiRequest<Profile>("GET", `${PROFILES}/${id}`);
}

/** POST /profiles. */
export function createProfile(body: ProfileCreate): Promise<Profile> {
  return apiRequest<Profile>("POST", PROFILES, body);
}

/** PATCH /profiles/{id}. */
export function updateProfile(id: string, body: ProfileUpdate): Promise<Profile> {
  return apiRequest<Profile>("PATCH", `${PROFILES}/${id}`, body);
}

/** DELETE /profiles/{id}: deletes everything that belongs to the profile. */
export function deleteProfile(id: string): Promise<void> {
  return apiRequest<void>("DELETE", `${PROFILES}/${id}`);
}

/** POST /profiles/{id}/favourites. */
export function addFavourite(profileId: string, body: FavouriteCreate): Promise<Favourite> {
  return apiRequest<Favourite>("POST", `${PROFILES}/${profileId}/favourites`, body);
}

/** DELETE /profiles/{id}/favourites/{favouriteId}. */
export function removeFavourite(profileId: string, favouriteId: string): Promise<void> {
  return apiRequest<void>("DELETE", `${PROFILES}/${profileId}/favourites/${favouriteId}`);
}

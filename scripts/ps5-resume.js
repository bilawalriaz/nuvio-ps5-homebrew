// EVO recreates the browser after playback. Resume the profile that opened Player
// once, rather than treating that browser as a new app launch.
const PS5_PLAYBACK_RETURN_KEY = "ps5_playback_return";
const ps5PlaybackReturn = globalThis.__NUVIO_PS5__
  ? LocalStore.get(PS5_PLAYBACK_RETURN_KEY, null) : null;
if (globalThis.__NUVIO_PS5__) LocalStore.remove(PS5_PLAYBACK_RETURN_KEY);

globalThis.__nuvioSavePlaybackReturn = function () {
  if (!globalThis.__NUVIO_PS5__) return;
  LocalStore.set(PS5_PLAYBACK_RETURN_KEY, {
    profileId: String(ProfileManager.getActiveProfileId()),
    resume: LocalStore.get("webos_last_resume_route", null),
    savedAt: Date.now()
  });
};

function canResumePs5Playback() {
  if (!ps5PlaybackReturn || !globalThis.__NUVIO_PS5__) return false;
  if (new URLSearchParams(window.location.search).get("nuvioPlaybackReturn") !== "1") return false;
  const age = Date.now() - Number(ps5PlaybackReturn.savedAt);
  if (!Number.isFinite(age) || age < 0 || age > 24 * 60 * 60 * 1000) return false;
  const id = String(ProfileManager.getActiveProfileId());
  if (ps5PlaybackReturn.profileId !== id) return false;
  const profiles = LocalStore.get("profiles", []);
  if (!Array.isArray(profiles) || !profiles.some(profile => String(profile.id) === id)) return false;
  const resume = ps5PlaybackReturn.resume;
  if (resume && Router.isWebOsResumeRouteRestorable(resume.route)) {
    // The route's normal 20-minute lifetime must not expire during a movie.
    LocalStore.set("webos_last_resume_route", { ...resume, savedAt: Date.now() });
  } else {
    LocalStore.remove("webos_last_resume_route");
  }
  return true;
}

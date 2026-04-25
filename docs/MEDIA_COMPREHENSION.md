# Media Comprehension Doctrine

## Property

Xion may later understand user-uploaded audio or video for a single turn by transcribing and summarizing it, without converting that capability into biometric learning or raw media memory.

## Invariants Touched

Strengthens Invariant 2 (`/forget`), Invariant 5 (no hidden economic pressure), Invariant 17 (sovereign fallback), and Invariant 18 (voice floor). Leaves the Genesis sensory posture unchanged.

## Scope

This is a Tier-2 scope document only. It adds no code, no verifier, no consent-field change, and no Agent Soul before Genesis.

## Future Consent Scope

The future consent field is `stream_uploaded_media`.

- Default: `False`.
- User-visible label: `Uploaded audio/video comprehension`.
- It is separate from `stream_voice` and `stream_visual`; a user may allow voice playback without allowing uploaded media analysis.

## Cost Preview Gate

Any turn that consumes uploaded audio or video must emit a `cost_preview` event and receive explicit user acceptance before inference begins. The unit is per-second-of-input, not per-token, because the user understands the length of their media before they understand the tokenized transcript.

No media bytes may be sent to a hosted multimodal model before the preview is accepted.

## Future Agent Soul Shape

The post-Genesis soul is `genesis/AGENT_SOULS/media-comprehension-agent.yaml`.

Allowed tools:

- `xion.media.transcribe_uploaded`
- `xion.media.summarize_transcript`

Forbidden tools:

- `xion.user_image.read_direct`
- `xion.media.store_raw_bytes`
- `xion.media.compute_voiceprint`
- `xion.media.compute_face_embedding`
- `hermes.tool.web_post`
- `hermes.tool.shell`

The forbidden list is load-bearing. It prevents uploaded-media comprehension from becoming biometric learning by accident.

## Forget Propagation

Raw uploaded media is never embedded. The first implementation may cache raw bytes only until the earlier of turn completion plus 60 seconds or user session end. `/forget` must delete:

- transcript rows
- summary rows
- raw media cache entries
- any pending job state that can reconstruct the media

Only the transcript and summary can enter normal text memory, and only under the user's existing memory consent.

## Pricing Extension

`GET /pricing` will eventually add `modality_costs.media_comprehension`, denominated per second of input. This price must be shown before upload processing begins.

## Non-Goals

This doctrine does not introduce raw audio/video learning, voiceprint storage, face embeddings, training on uploaded media, or a change to `docs/STATE_OF_XION_PRE_GENESIS.md` § "Sensory Posture At Genesis".

Media comprehension is per-turn comprehension. It is not biometric memory.

## Verification Path

The future verifier should check:

- `ModalityConsent` includes `stream_uploaded_media` defaulting to `False`.
- The media endpoint refuses processing without an accepted cost preview.
- Raw media cache paths are covered by `/forget`.
- The `media-comprehension-agent` forbids raw-byte storage, voiceprints, and face embeddings.

Until those checks exist, this document is doctrine only.

"use client"

import { useEffect, useRef, useState } from "react"
import { Loader2, Radio, TriangleAlert } from "lucide-react"


type PlayerState = "connecting" | "live" | "error" | "closed"

type WebRTCPlayerProps = {
  endpoint: string
  token: string
  muted?: boolean
  controls?: boolean
  className?: string
  onStateChange?: (state: PlayerState) => void
}

function waitForIceGathering(
  peerConnection: RTCPeerConnection,
  timeoutMs = 3000,
) {
  if (peerConnection.iceGatheringState === "complete") {
    return Promise.resolve()
  }

  return new Promise<void>((resolve) => {
    let settled = false

    const finish = () => {
      if (settled) return
      settled = true
      peerConnection.removeEventListener(
        "icegatheringstatechange",
        onChange,
      )
      resolve()
    }

    const onChange = () => {
      if (peerConnection.iceGatheringState === "complete") {
        finish()
      }
    }

    peerConnection.addEventListener(
      "icegatheringstatechange",
      onChange,
    )
    window.setTimeout(finish, timeoutMs)
  })
}

export function WebRTCPlayer({
  endpoint,
  token,
  muted = true,
  controls = false,
  className = "",
  onStateChange,
}: WebRTCPlayerProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const [state, setState] = useState<PlayerState>("connecting")
  const [message, setMessage] = useState("Connecting to live stream…")

  useEffect(() => {
    let cancelled = false
    let peerConnection: RTCPeerConnection | null = null
    let sessionUrl: string | null = null
    const abortController = new AbortController()

    const updateState = (next: PlayerState, text?: string) => {
      if (cancelled) return
      setState(next)
      if (text) setMessage(text)
      onStateChange?.(next)
    }

    async function connect() {
      updateState("connecting", "Connecting to live stream…")

      try {
        peerConnection = new RTCPeerConnection()
        const remoteStream = new MediaStream()

        peerConnection.addTransceiver("video", {
          direction: "recvonly",
        })
        peerConnection.addTransceiver("audio", {
          direction: "recvonly",
        })

        peerConnection.addEventListener("track", (event) => {
          if (event.streams[0]) {
            event.streams[0].getTracks().forEach((track) => {
              if (!remoteStream.getTracks().some((item) => item.id === track.id)) {
                remoteStream.addTrack(track)
              }
            })
          } else {
            remoteStream.addTrack(event.track)
          }

          if (videoRef.current) {
            videoRef.current.srcObject = remoteStream
            void videoRef.current.play().catch(() => undefined)
          }
        })

        peerConnection.addEventListener(
          "connectionstatechange",
          () => {
            if (!peerConnection) return

            if (peerConnection.connectionState === "connected") {
              updateState("live", "Live")
            }

            if (
              peerConnection.connectionState === "failed" ||
              peerConnection.connectionState === "disconnected"
            ) {
              updateState(
                "error",
                "Live video connection was interrupted.",
              )
            }
          },
        )

        const offer = await peerConnection.createOffer()
        await peerConnection.setLocalDescription(offer)
        await waitForIceGathering(peerConnection)

        const localDescription = peerConnection.localDescription
        if (!localDescription?.sdp) {
          throw new Error("Browser did not create a WebRTC offer.")
        }

        const response = await fetch(endpoint, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/sdp",
          },
          body: localDescription.sdp,
          signal: abortController.signal,
        })

        if (!response.ok) {
          const text = await response.text().catch(() => "")
          throw new Error(
            text || `Stream gateway returned HTTP ${response.status}.`,
          )
        }

        const locationHeader = response.headers.get("Location")
        if (locationHeader) {
          sessionUrl = new URL(locationHeader, endpoint).toString()
        }

        const answerSdp = await response.text()
        await peerConnection.setRemoteDescription({
          type: "answer",
          sdp: answerSdp,
        })
      } catch (error) {
        if (cancelled || abortController.signal.aborted) return
        updateState(
          "error",
          error instanceof Error
            ? error.message
            : "Unable to open the live stream.",
        )
      }
    }

    void connect()

    return () => {
      cancelled = true
      abortController.abort()

      if (sessionUrl) {
        void fetch(sessionUrl, {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
          keepalive: true,
        }).catch(() => undefined)
      }

      peerConnection?.close()
      if (videoRef.current) {
        videoRef.current.srcObject = null
      }
      onStateChange?.("closed")
    }
  }, [endpoint, token, onStateChange])

  return (
    <div className={`relative h-full w-full overflow-hidden bg-black ${className}`}>
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted={muted}
        controls={controls}
        className="h-full w-full object-contain"
      />

      {state === "connecting" && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-black/70 text-white">
          <Loader2 className="size-7 animate-spin" />
          <span className="text-sm">{message}</span>
        </div>
      )}

      {state === "error" && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-black/80 px-6 text-center text-white">
          <TriangleAlert className="size-8 text-amber-400" />
          <p className="max-w-md text-sm">{message}</p>
          <p className="text-xs text-white/55">
            Check camera availability, RTSP configuration and browser-compatible codec settings.
          </p>
        </div>
      )}

      {state === "live" && (
        <div className="pointer-events-none absolute left-3 top-3 flex items-center gap-2 rounded-full bg-black/60 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-white backdrop-blur">
          <Radio className="size-3.5 text-emerald-400" />
          Live
        </div>
      )}
    </div>
  )
}

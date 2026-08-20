export type LiveCamera = {
  camera_id: number
  camera_identifier: string
  name: string
  gis_location_id: number | null
  location_name: string | null
  latitude: number | null
  longitude: number | null
  status: string
  stream_status: string
  ai_enabled: boolean
  is_active: boolean
  assigned_jetson_identifier: string | null
  assigned_jetson_name: string | null
  field_nanostation_identifier: string | null
  stream_configured: boolean
  gateway_path: string
  gateway_ready: boolean | null
  viewer_count: number
  last_seen_at: string | null
  last_stream_check_at: string | null
}

export type LiveStreamListResponse = {
  items: LiveCamera[]
  total: number
  gateway_available: boolean
  generated_at: string
}

export type LiveStreamSession = {
  camera: LiveCamera
  protocol: "webrtc" | string
  gateway_path: string
  whep_url: string
  token: string
  expires_at: string
}

import { useEffect, useRef, useState } from 'react'
import type { IScannerControls } from '@zxing/browser'
import { Camera, X } from 'lucide-react'

type Props = {
  onCancel: () => void
  onRead: (pixCode: string) => void
}

export default function PixCameraScanner({ onCancel, onRead }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const controlsRef = useRef<IScannerControls | null>(null)
  const onReadRef = useRef(onRead)
  const [error, setError] = useState('')

  useEffect(() => { onReadRef.current = onRead }, [onRead])

  useEffect(() => {
    let mounted = true

    const openCamera = async () => {
      if (!videoRef.current) return
      try {
        const { BrowserQRCodeReader } = await import('@zxing/browser')
        const reader = new BrowserQRCodeReader(undefined, { delayBetweenScanAttempts: 250 })
        const controls = await reader.decodeFromConstraints(
          { audio: false, video: { facingMode: { ideal: 'environment' } } },
          videoRef.current,
          result => {
            if (!result || !mounted) return
            controlsRef.current?.stop()
            onReadRef.current(result.getText())
          },
        )
        if (mounted) controlsRef.current = controls
        else controls.stop()
      } catch (cameraError) {
        if (!mounted) return
        const denied = cameraError instanceof DOMException && cameraError.name === 'NotAllowedError'
        setError(denied
          ? 'Permita o acesso à câmera para ler o QR Code.'
          : 'Não foi possível abrir a câmera neste dispositivo.')
      }
    }

    openCamera()
    return () => {
      mounted = false
      controlsRef.current?.stop()
    }
  }, [])

  return <div className="bank-camera">
    <div className="bank-camera-title">
      <div><Camera /><span>Aponte para o QR Code</span></div>
      <button type="button" onClick={onCancel} aria-label="Fechar câmera"><X /></button>
    </div>
    <div className="bank-camera-preview">
      <video ref={videoRef} muted playsInline />
      <span className="bank-camera-frame" />
    </div>
    {error && <p className="bank-error">{error}</p>}
    <small>O código será identificado automaticamente.</small>
  </div>
}

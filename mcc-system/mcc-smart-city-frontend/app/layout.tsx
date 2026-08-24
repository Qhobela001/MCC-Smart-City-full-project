import { Analytics } from '@vercel/analytics/next'
import type { Metadata, Viewport } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import './globals.css'

import Image from 'next/image'

const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] })
const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
})

export const metadata: Metadata = {
  title:    'MCC Command Center | Maseru City Council',
  description:
      'Smart City monitoring and operations dashboard for the Maseru City Council — live feeds, AI incident alerts, analytics, and device health.',
  generator: 'v0.app',
}

export const viewport: Viewport = {
  colorScheme: 'light dark',
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: 'white' },
    { media: '(prefers-color-scheme: dark)', color: 'black' },
  ],
}

export default function RootLayout({
                                     children,
                                   }: Readonly<{
  children: React.ReactNode
}>) {
  return (
      <html
          lang="en"
          suppressHydrationWarning
          className={`${geistSans.variable} ${geistMono.variable} dark bg-background`}
      >
      <head>
        <script
            dangerouslySetInnerHTML={{
              __html: `try{var t=localStorage.getItem('theme');var d=document.documentElement;if(t==='light'){d.classList.remove('dark')}else{d.classList.add('dark')}}catch(e){}`,
            }}
        />
      </head>
      <body className="font-sans antialiased">

      {/* MCC Logo */}
      <div className="fixed top4 right4 z-50">
          <Image
              src="/mcc-logo1.png"
              alt="Maseru City Council Logo"
              width={60}
              height={80}
              priority
          />
      </div>

      {children}

      {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
      </html>
  )
}
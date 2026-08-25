import { Analytics } from "@vercel/analytics/next"
import type { Metadata,Viewport } from "next"
import { Geist,Geist_Mono } from "next/font/google"
import "./globals.css"
import { AuthProvider } from "@/components/auth/auth-provider"
const geistSans=Geist({variable:"--font-geist-sans",subsets:["latin"]});const geistMono=Geist_Mono({variable:"--font-geist-mono",subsets:["latin"]})
export const metadata:Metadata={title:"MCC Command Center | Maseru City Council",description:"Smart City monitoring and administration dashboard for Maseru City Council."}
export const viewport:Viewport={colorScheme:"light dark",themeColor:[{media:"(prefers-color-scheme: light)",color:"white"},{media:"(prefers-color-scheme: dark)",color:"#07111f"}]}
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en" suppressHydrationWarning className={`${geistSans.variable} ${geistMono.variable} dark bg-background`}><head><script dangerouslySetInnerHTML={{__html:`try{var t=localStorage.getItem('theme');var d=document.documentElement;if(t==='light'){d.classList.remove('dark')}else{d.classList.add('dark')}}catch(e){}`}}/></head><body className="font-sans antialiased"><AuthProvider>{children}</AuthProvider>{process.env.NODE_ENV==="production"&&<Analytics/>}</body></html>}

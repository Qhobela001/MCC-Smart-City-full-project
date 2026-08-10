"use client"
import Link from "next/link"
import { useEffect, useMemo, useState } from "react"
import { usePathname } from "next/navigation"
import * as Icons from "lucide-react"
import { ChevronRight, LogOut, ShieldCheck } from "lucide-react"
import { cn } from "@/lib/utils"
import { apiFetch } from "@/lib/api"
import type { NavigationItem } from "@/lib/types"
import { useAuth } from "@/components/auth/auth-provider"

const fallback:NavigationItem[]=[
{id:1,label:"Dashboard",href:"/",icon:"LayoutDashboard",section:"Overview",sort_order:1,is_active:true,is_system:true,created_at:""},
{id:2,label:"Users",href:"/administration/users",icon:"Users",section:"Administration",sort_order:1,is_active:true,is_system:true,created_at:""},
{id:3,label:"Departments",href:"/administration/departments",icon:"Building2",section:"Administration",sort_order:2,is_active:true,is_system:true,created_at:""},
{id:4,label:"Roles & Permissions",href:"/administration/roles",icon:"ShieldCheck",section:"Administration",sort_order:3,is_active:true,is_system:true,created_at:""},
{id:5,label:"Navigation",href:"/administration/navigation",icon:"PanelLeft",section:"Administration",sort_order:4,is_active:true,is_system:true,created_at:""},
]
function iconFor(name:string){return (Icons as unknown as Record<string,Icons.LucideIcon>)[name]||Icons.Circle}
function routeFor(href:string){return href==="/dashboard"?"/":href==="/monitoring/live"?"/live-feeds":href==="/reports"?"/analytics":href}
export function Sidebar(){const pathname=usePathname();const {user,logout}=useAuth();const [items,setItems]=useState<NavigationItem[]>([]);useEffect(()=>{apiFetch<NavigationItem[]>("/navigation/me").then(setItems).catch(()=>setItems(fallback))},[]);const groups=useMemo(()=>{const map=new Map<string,NavigationItem[]>();for(const item of items.filter(x=>x.is_active).sort((a,b)=>a.sort_order-b.sort_order)){const s=item.section||"Workspace";map.set(s,[...(map.get(s)||[]),item])}return [...map.entries()]},[items]);const initials=(user?.full_name||"MCC").split(/\s+/).map(x=>x[0]).slice(0,2).join("").toUpperCase();return <aside className="hidden w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar lg:flex"><div className="flex h-16 items-center gap-3 border-b border-sidebar-border px-5"><div className="flex size-9 items-center justify-center rounded-lg bg-primary/15 text-primary"><ShieldCheck className="size-5"/></div><div className="leading-tight"><p className="text-sm font-semibold text-sidebar-foreground">MCC Command</p><p className="text-xs text-muted-foreground">Maseru City Council</p></div></div><nav className="flex flex-1 flex-col overflow-y-auto px-3 py-4">{groups.map(([section,links])=><div key={section} className="mb-4"><p className="px-2 pb-2 text-[11px] font-semibold uppercase tracking-[.16em] text-muted-foreground">{section}</p><div className="space-y-1">{links.map(item=>{const Icon=iconFor(item.icon);const href=routeFor(item.href);const active=pathname===href||(href!=="/"&&pathname.startsWith(href));return <Link key={item.id} href={href} className={cn("group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition",active?"bg-primary/12 font-medium text-primary":"text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-foreground")}><Icon className="size-4"/><span className="flex-1">{item.label}</span><ChevronRight className={cn("size-3.5 opacity-0 transition group-hover:opacity-70",active&&"opacity-70")}/></Link>})}</div></div>)}</nav><div className="border-t border-sidebar-border p-3"><div className="rounded-xl bg-sidebar-accent/55 p-3"><div className="flex items-center gap-3"><div className="flex size-9 items-center justify-center rounded-full bg-primary/15 text-xs font-bold text-primary">{initials}</div><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{user?.full_name}</p><p className="truncate text-xs text-muted-foreground">{user?.is_superuser?"Super Administrator":user?.role?.name||"MCC Employee"}</p></div><button onClick={logout} title="Sign out" className="rounded-md p-2 text-muted-foreground hover:bg-background hover:text-foreground"><LogOut className="size-4"/></button></div></div></div></aside>}

"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";

import { api, type Me } from "@/lib/api";
import { isSignedIn, signOut } from "@/lib/auth";

import { Logo } from "./Brand";

export function Header({ me }: { me?: Me | null }) {
  const path = usePathname();
  const counsellor = me?.memberships.some((m) => m.kind === "counselling");
  const links = [
    { href: "/letters/", label: "My letters" },
    ...(counsellor ? [{ href: "/counsellor/", label: "Case inbox" }] : []),
    { href: "/settings/", label: "Settings" },
  ];
  return (
    <header className="header">
      <div className="container">
        <Link href={me ? "/letters/" : "/"} className="brand">

"use client";
import dynamic from "next/dynamic";

const DashboardClient = dynamic(() => import("./DashboardClient"), { ssr: false });

export default function ClientWrapper({ userId }: { userId: string }) {
    return <DashboardClient userId={userId} />;
}

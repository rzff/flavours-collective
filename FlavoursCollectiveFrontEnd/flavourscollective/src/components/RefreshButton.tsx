"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export default function RefreshButton() {
  const router = useRouter();
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = () => {
    setIsRefreshing(true);
    // window.location.reload() is the "hammer" that forces a fresh
    // fetch from Java, bypasses all Next.js client-side caching.
    window.location.reload();
  };

  return (
    <button
      onClick={handleRefresh}
      disabled={isRefreshing}
      className={`text-sm font-medium px-5 py-2.5 rounded-lg border transition-all shadow-sm
        ${
          isRefreshing
            ? "bg-gray-100 text-gray-400 cursor-not-allowed"
            : "bg-white text-gray-700 hover:bg-gray-50 border-gray-300 active:scale-95"
        }`}
    >
      {isRefreshing ? "Refreshing..." : "Refresh List"}
    </button>
  );
}

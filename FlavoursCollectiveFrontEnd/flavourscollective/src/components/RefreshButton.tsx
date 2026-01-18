"use client"; // This tells Next.js this is a Client Component

export default function RefreshButton() {
  return (
    <button
      onClick={() => window.location.reload()}
      className="text-sm bg-white border px-4 py-2 rounded-md hover:bg-gray-50 shadow-sm transition-colors text-gray-700"
    >
      Refresh List
    </button>
  );
}

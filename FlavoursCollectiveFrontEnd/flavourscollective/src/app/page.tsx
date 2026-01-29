import { Product } from "@/types/product";
import RefreshButton from "@/components/RefreshButton";

export const dynamic = "force-dynamic";

async function getProducts(): Promise<Product[]> {
  try {
    // Inside Docker, containers talk to each other via their service names
    const res = await fetch("http://orchestrator:8080/api/products", {
      cache: "no-store",
    });
    if (!res.ok) {
      console.error("Fetch failed with status:", res.status);
      return [];
    }
    return res.json();
  } catch (e) {
    console.error("Fetch error:", e);
    return [];
  }
}

export default async function Home() {
  const products = await getProducts();

  return (
    <main className="p-8 bg-gray-50 min-h-screen">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-end mb-8">
          <div>
            <h1 className="text-4xl font-bold text-gray-900">
              Product Archive
            </h1>
            <p className="text-gray-600">
              Showing {products.length} items from your Postgres database.
            </p>
          </div>

          {/* Use the client component here */}
          <RefreshButton />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {products.map((product) => (
            <div
              key={product.id}
              className="bg-white p-4 rounded-xl border shadow-sm group"
            >
              <div className="overflow-hidden rounded-md mb-4 bg-gray-100 aspect-square">
                <img
                  src={product.imageUrl || "https://via.placeholder.com/400"}
                  alt={product.name}
                  className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
                />
              </div>
              <h2 className="font-bold truncate text-gray-800">
                {product.name}
              </h2>
              <p className="text-indigo-600 font-semibold">{product.price}</p>
              <p className="text-xs text-gray-400 mt-2 italic">
                ID: {product.id} •{" "}
                {new Date(product.extractedAt).toLocaleDateString()}
              </p>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}

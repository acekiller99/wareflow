export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <h1 className="text-4xl font-bold mb-4">WareFlow</h1>
      <p className="text-gray-600 text-lg">Warehouse Management System</p>
      <div className="mt-8 grid grid-cols-2 md:grid-cols-3 gap-4">
        {[
          { href: "/inventory", label: "Inventory" },
          { href: "/products", label: "Products" },
          { href: "/inbound", label: "Inbound" },
          { href: "/outbound", label: "Outbound" },
          { href: "/transfers", label: "Transfers" },
          { href: "/counts", label: "Stock Counts" },
          { href: "/suppliers", label: "Suppliers" },
          { href: "/reports", label: "Reports" },
          { href: "/scan", label: "Quick Scan" },
        ].map((item) => (
          <a
            key={item.href}
            href={item.href}
            className="block p-6 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow text-center"
          >
            <span className="text-lg font-medium">{item.label}</span>
          </a>
        ))}
      </div>
    </main>
  );
}

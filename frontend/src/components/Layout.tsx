import type { ReactNode } from "react";
import Header from "./Header";

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <>
      <Header />
      <main
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          padding: "24px 20px 60px",
        }}
      >
        <div style={{ width: "100%", maxWidth: 1100 }}>{children}</div>
      </main>
    </>
  );
}

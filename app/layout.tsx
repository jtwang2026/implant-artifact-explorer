import type { Metadata } from "next";
import "./globals.css";
import "./trajectory.css";
import "./playground/playground.css";
import "./geometry/geometry.css";
import "./kb/kb.css";
import "./sim/sim.css";

export const metadata: Metadata = {
  title: "植位智探｜CBCT 伪影科学探索环境",
  description: "从厂家规格、参数化 CAD、虚拟植入到 CBCT 物理仿真与 Agent 几何探索的真实环境回放。",
  openGraph: { title: "植位智探", description: "让 Agent 探索可检验，也可被推翻", images: ["/og.png"] },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="zh-CN"><body>{children}</body></html>;
}

import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = {
  title: '西大 · 云游校园',
  icons: { icon: `${process.env.NEXT_PUBLIC_BASE_PATH ?? ''}/favicon.svg` },
  description:
    '广西大学主校区三维地图，支持地标搜索、自动巡游和昼夜切换。使用 Three.js 和 Blender 制作。',
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}

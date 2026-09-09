import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = {
  title: '西大 · 云游校园',
  icons: { icon: `${process.env.NEXT_PUBLIC_BASE_PATH ?? ''}/favicon.svg` },
  description:
    '以真实地理数据与 Blender 建筑模型，探索广西大学的林荫、湖塘与校园建筑。',
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

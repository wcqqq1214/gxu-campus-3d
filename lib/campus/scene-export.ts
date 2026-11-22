/**
 * Download the rendered canvas as a PNG with an attribution footer. The caller
 * must render the frame immediately before, since the drawing buffer is not
 * preserved between frames.
 */
export async function downloadCanvas(
  canvas: HTMLCanvasElement,
  segments: string[],
  filename: string,
) {
  const out = document.createElement('canvas');
  out.width = canvas.width;
  out.height = canvas.height;
  const ctx = out.getContext('2d');
  if (!ctx) throw new Error('Canvas unavailable');
  ctx.drawImage(canvas, 0, 0);
  const size = Math.max(15, Math.round(out.width / 110));
  ctx.font = `${size}px sans-serif`;
  const label = segments.join('  |  ');
  const available = out.width - size * 2;
  const lines = ctx.measureText(label).width <= available ? [label] : segments;
  const lineHeight = size * 1.5;
  const footerHeight = lineHeight * lines.length + size;
  ctx.fillStyle = '#1d3b31dd'; // Radix jade-12
  ctx.fillRect(0, out.height - footerHeight, out.width, footerHeight);
  ctx.fillStyle = 'white';
  for (let i = 0; i < lines.length; i++) {
    ctx.font = `${size}px sans-serif`;
    const fittedSize = Math.min(
      size,
      (size * available) / ctx.measureText(lines[i]).width,
    );
    ctx.font = `${fittedSize}px sans-serif`;
    ctx.fillText(
      lines[i],
      size,
      out.height - footerHeight + size + lineHeight * i,
    );
  }
  const blob = await new Promise<Blob | null>((resolve) =>
    out.toBlob(resolve, 'image/png'),
  );
  if (!blob) throw new Error('Export failed');
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// Runs inside the browser so a delayed automation read cannot lose a publication.
// Missing publications in the page remain missing; the caller validates indices.
export function beginBenchmarkCapture() {
  const element = document.querySelector('.debug-metrics');
  if (!element) throw Error('Missing benchmark metrics element');
  const samples = [];
  let lastIndex = 0;
  const observer = new MutationObserver(() => {
    const metric = JSON.parse(element.textContent);
    const benchmark = metric.benchmark;
    if (!benchmark?.orbiting || benchmark.sampleIndex <= lastIndex) return;
    lastIndex = benchmark.sampleIndex;
    samples.push(metric);
  });
  observer.observe(element, {
    childList: true,
    characterData: true,
    subtree: true,
  });
  return { samples, observer };
}

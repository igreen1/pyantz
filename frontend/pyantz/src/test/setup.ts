import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

// react flow measures what it draws; jsdom can't, so give it what it needs
// (see reactflow.dev/learn/advanced-use/testing)
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverStub;

class DOMMatrixReadOnlyStub {
  m22: number;
  constructor(transform?: string) {
    const scale = transform?.match(/scale\(([1-9.]+)\)/)?.[1];
    this.m22 = scale === undefined ? 1 : Number(scale);
  }
}
(globalThis as unknown as { DOMMatrixReadOnly: unknown }).DOMMatrixReadOnly =
  DOMMatrixReadOnlyStub;

Object.defineProperties(globalThis.HTMLElement.prototype, {
  offsetHeight: {
    get() {
      return Number.parseFloat(this.style.height) || 100;
    },
  },
  offsetWidth: {
    get() {
      return Number.parseFloat(this.style.width) || 200;
    },
  },
});
(
  globalThis.SVGElement.prototype as unknown as { getBBox: () => object }
).getBBox = () => ({ x: 0, y: 0, width: 0, height: 0 });

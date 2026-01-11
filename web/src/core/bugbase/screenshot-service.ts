// Copyright (c) 2025 Galaxy Technology Service
// BugBase Screenshot Service - Captures viewport screenshots using html2canvas

export interface ScreenshotResult {
    dataUrl: string;
    width: number;
    height: number;
    timestamp: number;
}

export interface ScreenshotOptions {
    quality?: number; // 0-1, default 0.8
    maxWidth?: number; // Max width to resize to, default 1920
}

/**
 * Captures a screenshot of the current viewport
 * Returns null if capture fails (instead of throwing)
 */
export async function captureScreenshot(
    options: ScreenshotOptions = {}
): Promise<ScreenshotResult | null> {
    const { quality = 0.8, maxWidth = 1920 } = options;

    try {
        // Dynamic import html2canvas-pro (supports oklab/oklch colors)
        const html2canvas = (await import('html2canvas-pro')).default;

        // Capture the viewport with minimal options for better compatibility
        const canvas = await html2canvas(document.body, {
            useCORS: true,
            allowTaint: true,
            logging: false,
            scale: 1, // Use 1 for better compatibility
            backgroundColor: '#ffffff',
            ignoreElements: (element: Element) => {
                // Ignore the report button itself
                return element.hasAttribute('data-bugbase-ignore');
            },
        });

        // Resize if too large
        let finalCanvas = canvas;
        if (canvas.width > maxWidth) {
            const ratio = maxWidth / canvas.width;
            const resizedCanvas = document.createElement('canvas');
            resizedCanvas.width = maxWidth;
            resizedCanvas.height = canvas.height * ratio;
            const ctx = resizedCanvas.getContext('2d');
            if (ctx) {
                ctx.drawImage(canvas, 0, 0, resizedCanvas.width, resizedCanvas.height);
                finalCanvas = resizedCanvas;
            }
        }

        // Convert to data URL
        const dataUrl = finalCanvas.toDataURL('image/png', quality);

        return {
            dataUrl,
            width: finalCanvas.width,
            height: finalCanvas.height,
            timestamp: Date.now(),
        };
    } catch (error) {
        console.warn('[BugBase] Screenshot capture failed:', error);
        // Return null instead of throwing - form will still open
        return null;
    }
}

/**
 * Converts base64 data URL to Blob for upload
 */
export function dataUrlToBlob(dataUrl: string): Blob {
    const [header, base64] = dataUrl.split(',');
    const mimeMatch = header?.match(/data:([^;]+);/);
    const mime = mimeMatch?.[1] || 'image/png';
    const binary = atob(base64 || '');
    const array = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        array[i] = binary.charCodeAt(i);
    }
    return new Blob([array], { type: mime });
}

/**
 * Estimates the size of a base64 data URL in bytes
 */
export function estimateDataUrlSize(dataUrl: string): number {
    const base64 = dataUrl.split(',')[1] || '';
    return Math.ceil((base64.length * 3) / 4);
}

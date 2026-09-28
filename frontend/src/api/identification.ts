import { isAxiosError } from 'axios';

import { http } from '@/api/http';

import type { PlantIdentificationResponse } from '@/types/identification';

const SUPPORTED_IMAGE_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp']);
export const IDENTIFICATION_MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024;
const MAX_SIDE_PX = 1600;

/**
 * Redraws the photo onto a canvas and saves it as a new JPEG. The copy has no
 * metadata, so GPS location and camera details never leave the device.
 */
async function withoutMetadata(image: File): Promise<Blob> {
  try {
    const bitmap = await createImageBitmap(image, { imageOrientation: 'from-image' });
    const scale = Math.min(1, MAX_SIDE_PX / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext('2d')?.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close();
    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, 'image/jpeg', 0.9),
    );
    if (blob) return blob;
  } catch {
    // Fall through: the server also strips metadata before sending anything on.
  }
  return image;
}

export async function identifyPlant(image: File): Promise<PlantIdentificationResponse> {
  if (!(image instanceof File)) {
    throw new TypeError('image must be a File.');
  }

  if (!SUPPORTED_IMAGE_TYPES.has(image.type)) {
    throw new TypeError('image must be a JPEG, PNG, or WebP file.');
  }

  if (image.size > IDENTIFICATION_MAX_IMAGE_SIZE_BYTES) {
    throw new RangeError('image must not exceed 10 MB.');
  }

  const formData = new FormData();
  formData.append('image', await withoutMetadata(image), 'photo.jpg');

  const { data } = await http.post<PlantIdentificationResponse>('/plants/identify', formData, {
    timeout: 45_000,
  });

  return data;
}

/** A user-facing message for a failed identification. */
export function identificationErrorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    const detail = (error.response?.data as { detail?: unknown } | undefined)?.detail;
    if (typeof detail === 'string') return detail;
  }
  return 'We couldn’t identify this plant. Please try again.';
}

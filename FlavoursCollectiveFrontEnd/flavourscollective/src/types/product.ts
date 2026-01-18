export interface Product {
  id: number;
  scrapeResponseId?: number;
  name: string;
  url: string;
  price: string;
  imageUrl: string;
  description: string;
  inStock: boolean;
  extractedAt: string; // JSON serializes LocalDateTime as a string
}

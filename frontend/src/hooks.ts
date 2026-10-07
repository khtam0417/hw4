import { useCallback, useEffect, useState } from 'react'
import { ApiError, fetchProduct, fetchProducts } from './api.ts'
import type { Product } from './types.ts'

// The catalogue is fetched once and shared by every page, so moving around the site doesn't reload it.
let cachedProducts: Product[] | null = null
let pendingProducts: Promise<Product[]> | null = null

function loadProducts(): Promise<Product[]> {
  pendingProducts ??= fetchProducts().then(
    (products) => {
      cachedProducts = products
      return products
    },
    (error: unknown) => {
      pendingProducts = null // let the next attempt try again
      throw error
    },
  )
  return pendingProducts
}

export function useProducts() {
  const [products, setProducts] = useState<Product[] | null>(cachedProducts)
  const [failed, setFailed] = useState(false)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (cachedProducts) return
    let active = true
    loadProducts().then(
      (items) => active && setProducts(items),
      () => active && setFailed(true),
    )
    return () => {
      active = false
    }
  }, [attempt])

  const retry = useCallback(() => {
    setFailed(false)
    setAttempt((n) => n + 1)
  }, [])

  return { products, failed, retry }
}

export type ProductState =
  | { status: 'loading' }
  | { status: 'ready'; product: Product }
  | { status: 'not-found' }
  | { status: 'error' }

/** One product with fresh stock from /api/products/{id}. The cached catalogue copy shows while it loads. */
export function useProduct(productId: string) {
  const [result, setResult] = useState<{ productId: string; state: ProductState } | null>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let active = true
    fetchProduct(productId).then(
      (product) => active && setResult({ productId, state: { status: 'ready', product } }),
      (error: unknown) => {
        if (!active) return
        const notFound = error instanceof ApiError && error.status === 404
        setResult({ productId, state: { status: notFound ? 'not-found' : 'error' } })
      },
    )
    return () => {
      active = false
    }
  }, [productId, attempt])

  const retry = useCallback(() => {
    setResult(null)
    setAttempt((n) => n + 1)
  }, [])

  let state: ProductState = { status: 'loading' }
  if (result?.productId === productId) {
    state = result.state
  } else {
    const cached = cachedProducts?.find((p) => p.product_id === productId)
    if (cached) state = { status: 'ready', product: cached }
  }
  return { state, retry }
}

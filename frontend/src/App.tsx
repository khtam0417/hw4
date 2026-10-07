import { createBrowserRouter, RouterProvider } from 'react-router'
import Layout from './components/Layout.tsx'
import AboutPage from './pages/AboutPage.tsx'
import CreateAccountPage from './pages/CreateAccountPage.tsx'
import HomePage from './pages/HomePage.tsx'
import LoginPage from './pages/LoginPage.tsx'
import NotFoundPage from './pages/NotFoundPage.tsx'
import ProductPage from './pages/ProductPage.tsx'
import ProductsPage from './pages/ProductsPage.tsx'
import SearchResultsPage from './pages/SearchResultsPage.tsx'

const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'products', element: <ProductsPage /> },
      { path: 'products/:productId', element: <ProductPage /> },
      { path: 'search', element: <SearchResultsPage /> },
      { path: 'about', element: <AboutPage /> },
      { path: 'login', element: <LoginPage /> },
      { path: 'create-account', element: <CreateAccountPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}

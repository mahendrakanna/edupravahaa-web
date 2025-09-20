import { useState, useCallback } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import toast from 'react-hot-toast'
import UILoader from '@src/@core/components/ui-loader'

/**
 * Custom hook for handling API calls with loading states and toast notifications
 * @param {Function} apiAction - Redux thunk action to dispatch
 * @param {Object} options - Configuration options
 * @returns {Object} - { execute, loading, error, data }
 */
export const useApiWithToast = (apiAction, options = {}) => {
  const dispatch = useDispatch()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)

  const {
    showLoader = true,
    showSuccessToast = true,
    showErrorToast = true,
    successMessage = null,
    errorMessage = null,
    onSuccess = null,
    onError = null
  } = options

  const execute = useCallback(async (payload) => {
    setLoading(true)
    setError(null)
    setData(null)

    try {
      const result = await dispatch(apiAction(payload)).unwrap()
      
      setData(result)
      
      // Show success toast if enabled and message exists
      if (showSuccessToast && result.message) {
        const message = successMessage || result.message
        const messageType = result.message_type || 'success'
        
        if (messageType === 'success') {
          toast.success(message)
        } else if (messageType === 'info') {
          toast(message, { icon: 'ℹ️' })
        } else if (messageType === 'warning') {
          toast(message, { icon: '⚠️' })
        } else {
          toast.success(message)
        }
      }
      
      // Call success callback if provided
      if (onSuccess) {
        onSuccess(result)
      }
      
      return result
    } catch (err) {
      const errorMsg = err?.message || err?.error || 'An error occurred'
      setError(errorMsg)
      
      // Show error toast if enabled
      if (showErrorToast) {
        const message = errorMessage || errorMsg
        toast.error(message)
      }
      
      // Call error callback if provided
      if (onError) {
        onError(err)
      }
      
      throw err
    } finally {
      setLoading(false)
    }
  }, [dispatch, apiAction, showLoader, showSuccessToast, showErrorToast, successMessage, errorMessage, onSuccess, onError])

  return {
    execute,
    loading,
    error,
    data
  }
}

/**
 * Higher-order component to wrap components with loading overlay
 * @param {React.Component} WrappedComponent - Component to wrap
 * @param {Object} options - Loading options
 * @returns {React.Component} - Wrapped component with loading overlay
 */
export const withApiLoader = (WrappedComponent, options = {}) => {
  const { 
    loadingSelector = null,
    overlayColor = 'rgba(255, 255, 255, 0.8)',
    loader = null
  } = options

  return function ApiLoaderWrapper(props) {
    const loading = loadingSelector ? useSelector(loadingSelector) : false

    return (
      <UILoader 
        blocking={loading} 
        overlayColor={overlayColor}
        loader={loader}
      >
        <WrappedComponent {...props} />
      </UILoader>
    )
  }
}

export default useApiWithToast

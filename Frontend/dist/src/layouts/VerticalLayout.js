// ** React Imports
import { Outlet } from 'react-router-dom'

// ** Core Layout Import
// !Do not remove the Layout import
import Layout from '@layouts/VerticalLayout'

// ** Menu Items Array
import navigation from '@src/navigation/vertical'
import { useSelector } from 'react-redux'

const VerticalLayout = props => {
  const userRole = useSelector(state => state.auth.user?.role)
  const enrolled = useSelector(state => state.auth.user)

  // const [menuData, setMenuData] = useState([])

  // ** For ServerSide navigation
  // useEffect(() => {
  //   axios.get(URL).then(response => setMenuData(response.data))
  // }, [])
  console.log('userRole',enrolled)
  const filteredMenuData = navigation
  .filter(item => !item.roles || item.roles.includes(userRole))
  .map(item => {
    if (userRole === 'student' && enrolled === false) {
      // Only enable 'courses' tab, disable others
      if (item.id === 'courses') {
        return { ...item, disabled: false }
      }
      return { ...item, disabled: true }
    }
    return { ...item, disabled: false }
  })
  console.log('filteredMenuData',filteredMenuData,"enrolled",enrolled)
  return (
    <Layout menuData={filteredMenuData} {...props}>
      <Outlet />
    </Layout>
  )
}

export default VerticalLayout

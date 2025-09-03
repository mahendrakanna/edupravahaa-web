// ** Vertical Menu Components
import VerticalNavMenuLink from './VerticalNavMenuLink'
import VerticalNavMenuGroup from './VerticalNavMenuGroup'
import VerticalNavMenuSectionHeader from './VerticalNavMenuSectionHeader'

// ** Utils
import {
  canViewMenuItem,
  canViewMenuGroup,
  resolveVerticalNavMenuItemComponent as resolveNavItemComponent
} from '@layouts/utils'

const VerticalMenuNavItems = props => {
  // ** Components Object
  const Components = {
    VerticalNavMenuLink,
    VerticalNavMenuGroup,
    VerticalNavMenuSectionHeader
  }


  // ** Render Nav Menu Items
  const RenderNavItems = props.items.map((item, index) => {
    const TagName = Components[resolveNavItemComponent(item)]
     const itemProps = { ...props, item, index, key: item.id || item.header, disabled: item.disabled }
    // if (item.children) {
    //   return canViewMenuGroup(item) && <TagName item={item} index={index} key={item.id} {...props} />
    // }
    // return canViewMenuItem(item) && <TagName key={item.id || item.header} item={item} {...props} />

     if (item.children) {
      return <TagName {...itemProps} />
    }
    return <TagName {...itemProps} />
  })
  

  return RenderNavItems
}

export default VerticalMenuNavItems

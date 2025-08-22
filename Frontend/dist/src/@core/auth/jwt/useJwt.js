// ** JWT Service Import
import JwtService from './jwtService'

// ** Export Service as useJwt
export default function useJwt(jwtOverrideConfig) {
  console.log("use jwt function is called in the useJwt class", jwtOverrideConfig)
  const jwt = new JwtService(jwtOverrideConfig)
  console.log("returned jwt-- ", jwt)
  return {
    jwt
  }
}

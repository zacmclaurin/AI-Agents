IRONROAD_CONTEXT = """
PROJECT: Iron Road
TYPE: Motorcycle riding social app
STATUS: ~93-95% complete, preparing for beta / TestFlight

STACK:
- Frontend: React Native, Expo SDK 54, TypeScript, Expo Router
- Backend: Supabase (auth, storage, realtime, 16 tables)
- Deployment: EAS (iOS), Netlify (web/waitlist)
- Payments: RevenueCat (planned, not yet integrated)
- Bundle ID: com.searchdevice.IronRoad
- Repo: github.com/zacmclaurin/IronRoad
- Local path: C:\\Users\\zzac0\\IronRoad

DESIGN SYSTEM:
- Background: #0d0d0d
- Primary red: #C0392B
- Text: #f0ece4
- Icons: Ionicons + custom SVGs

KEY FEATURES BUILT:
- Ride sharing and route planning (OSRM turn-by-turn)
- Weather along route (Open-Meteo)
- Direct messaging (Supabase Realtime)
- Events with flyer upload and admin approval
- Pro subscription (14-day trial, Supabase trigger)
- Referral/discount code system
- My Bike screen with photo upload
- Profile with avatar, bike photo banner, ride history
- Friends, Patches, Notifications, Help & Support
- Admin panel (user ID: 82fc6ab8-fbda-40be-bee5-6cb67b0eb991)

KNOWN TECHNICAL GOTCHAS:
- File uploads: must use expo-file-system/legacy with readAsStringAsync + base64 + base64-arraybuffer decode
- FileSystem.EncodingType.Base64 is undefined at runtime — use string literal 'base64'
- Nominatim geocoding requires User-Agent: 'IronRoad/1.0' header
- All Supabase tables need explicit GRANT ALL ON public.table TO anon, authenticated
- Pro gate currently bypassed: lib/subscription.ts isProUser always returns true (BETA TESTING comment)

IMMEDIATE TODO:
- Fix address autocomplete persistence bug
- Integrate RevenueCat (revert beta bypass in lib/subscription.ts first)
- Cut new EAS build
- Distribute via TestFlight to beta riders

BUSINESS:
- LLC filing pending in South Carolina
- Domain: ironroad.app (to purchase)
- Support email: support@ironroad.app
- Business banking: Mercury (planned)
- Owner: Zac McLaurin (GitHub: zacmclaurin, Expo: searchdevice)
"""

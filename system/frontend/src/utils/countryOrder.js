export const GLOBAL_PLUS_PRIORITY_COUNTRIES = [
  'STLCs',
  'EU27',
  'China',
  'Germany',
  'India',
  'Japan',
  'Russia',
  'United Kingdom',
  'United States'
]

export function orderCountriesForVersion(countries, versionMode = 'global', options = {}) {
  const uniqueCountries = Array.from(new Set((countries || []).filter(Boolean)))
  const sortedCountries = [...uniqueCountries].sort((a, b) => a.localeCompare(b))
  const baseCountries = options.sort === false ? uniqueCountries : sortedCountries

  if (versionMode !== 'global_plus') {
    return baseCountries
  }

  const countrySet = new Set(baseCountries)
  const priorityCountries = GLOBAL_PLUS_PRIORITY_COUNTRIES.filter(country => countrySet.has(country))
  const prioritySet = new Set(priorityCountries)
  const remainingCountries = sortedCountries.filter(country => !prioritySet.has(country))

  return [...priorityCountries, ...remainingCountries]
}

// Enable debug in localStorage
if (typeof window !== 'undefined') {
  localStorage.setItem('pm:debug:enabled', 'true');
  localStorage.setItem('pm:debug:categories', JSON.stringify(['all']));
  console.log('Debug enabled! Refresh the page.');
}

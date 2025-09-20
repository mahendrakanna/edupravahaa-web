import React from 'react'
import '@styles/base/core/menu/menu-types/vertical-overlay-menu.scss'

const TrialBanner = ({ trialPeriodData, remainingTime }) => {
  if (!trialPeriodData || !trialPeriodData.is_trial || trialPeriodData.has_purchased) return null

  return (
     <div className="trial-banner-fixed">
      <div className="scrolling-text">
        🎉 Your trial is active! Ends on{" "}
        <strong>{new Date(trialPeriodData.trial_ends_at).toLocaleString()}</strong> ⏳ | 
        Remaining Time: <strong>{remainingTime}</strong>
      </div>
    </div>
  )
}

export default TrialBanner
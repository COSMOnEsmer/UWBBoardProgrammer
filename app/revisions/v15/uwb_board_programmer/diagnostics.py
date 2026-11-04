"""User-facing explanations. These do not change or approve solver outputs."""


def diagnostic_lines(state,tr=lambda value:value):
    if state.get('diagnostic'):
        return [tr('Diagnostic capture is active. Close capture, then connect from Live positioning to calculate positions.')]
    if not state.get('running'):
        return [tr('Reception is open. Press Start positioning to calculate Tag coordinates.')]
    lines=[tr('Position processing is running. Repeated Start commands do not reset synchronization.')]
    lines.append(tr('Complete BLINK groups evaluated')+': '+str(state.get('solver_attempts',0))+
                 ' | '+tr('Rejected groups/events')+': '+str(state.get('rejected',0)))
    failed=state.get('last_solver_rejection')
    if failed:
        lines.append(tr('Latest position rejection')+': '+tr(failed['reason']))
        details=failed.get('details',{})
        if 'z_uncertainty_m' in details:
            lines.append(tr('Measured Z 95% uncertainty')+f": {details['z_uncertainty_m']:.2f} m | "+
                         tr('Allowed maximum')+f": {details['max_z_uncertainty_m']:.2f} m")
        if 'horizontal_uncertainty_m' in details:
            lines.append(tr('Measured horizontal 95% uncertainty')+f": {details['horizontal_uncertainty_m']:.2f} m | "+
                         tr('Allowed maximum')+f": {details['max_horizontal_uncertainty_m']:.2f} m")
    elif not state.get('fixes'):
        lines.append(tr('No complete validated BLINK group has reached the solver yet.'))
    for aid,clock in state.get('clocks',{}).items():
        reason=clock.get('not_ready_reason','')
        if not clock.get('ready') and reason:
            noise=clock.get('rms_ns')
            lines.append(aid+': '+tr(reason)+(f' ({noise:.2f} ns)' if noise is not None and '2 ns' in reason else ''))
    return lines

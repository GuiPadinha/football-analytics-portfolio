-- One row per outfield player, club and season with at least `min_minutes` on the pitch:
-- season counts and per-90 rates. The SQL twin of src/similarity.py
-- `build_player_per90_features`, built from the raw events and lineups.
select * from ({{ season_per90(outfield_actions(), extra_counts=['goals']) }})
where position_group <> 'Goalkeeper'

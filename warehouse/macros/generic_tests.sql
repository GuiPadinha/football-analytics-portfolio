{# Two small generic tests, written here rather than pulling in dbt_utils for them. #}

{% test probability(model, column_name) %}
-- Fails on any value outside [0, 1]; nulls are not_null's job.
select {{ column_name }}
from {{ model }}
where {{ column_name }} < 0 or {{ column_name }} > 1
{% endtest %}

{% test unique_together(model, columns) %}
-- Fails on every combination of `columns` that appears more than once.
select {{ columns | join(', ') }}, count(*) as n
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1
{% endtest %}

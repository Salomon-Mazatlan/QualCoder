# -*- coding: utf-8 -*-

"""
This file is part of QualCoder.

QualCoder is free software: you can redistribute it and/or modify it under the
terms of the GNU Lesser General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later version.

QualCoder is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with QualCoder.
If not, see <https://www.gnu.org/licenses/>.

Author: Kai Droege (kaixxx)
https://github.com/ccbogel/QualCoder
https://qualcoder.wordpress.com/
https://qualcoder.org/
"""

import datetime
import logging
import os
import sqlite3

logger = logging.getLogger(__name__)

# Task labels used to group the consumption per QualCoder feature.
TASK_CHAT = 'chat'
TASK_SEARCH_DESCRIPTIONS = 'search_descriptions'
TASK_SEARCH_ANALYZE = 'search_analyze'
TASK_OTHER = 'other'

# Rough fallback: about 4 characters per token (the same heuristic used elsewhere
# in QualCoder when a real token count is not available).
CHARS_PER_TOKEN = 4


def _estimate_text_tokens(text) -> int:
    """
    Very rough token estimate based on character length.
    Used only as a fallback when neither the provider nor the model tokenizer
    give us a real count.
    """
    
    if not text:
        return 0
    return max(1, round(len(str(text)) / CHARS_PER_TOKEN))


def _extract_real_usage(response) -> dict | None:
    """
    Try to read the real token usage reported by the provider from a
    LangChain message (or message chunk).

    Returns a dict {input, output, total} or None if no usage information is
    available (e.g. some providers do not report usage while streaming).
    """
    
    if response is None:
        return None
    # 1) Standard LangChain usage_metadata (OpenAI, Anthropic, Gemini, ...)
    usage = getattr(response, 'usage_metadata', None)
    if isinstance(usage, dict) and usage.get('total_tokens'):
        return {
            'input': int(usage.get('input_tokens', 0) or 0),
            'output': int(usage.get('output_tokens', 0) or 0),
            'total': int(usage.get('total_tokens', 0) or 0),
        }
    # 2) Provider specific data inside response_metadata
    meta = getattr(response, 'response_metadata', None)
    if isinstance(meta, dict):
        token_usage = meta.get('token_usage') or meta.get('usage')
        if isinstance(token_usage, dict):
            prompt = int(token_usage.get('prompt_tokens', 0) or 0)
            completion = int(token_usage.get('completion_tokens', 0) or 0)
            total = int(token_usage.get('total_tokens', prompt + completion) or 0)
            if total > 0:
                return {'input': prompt, 'output': completion, 'total': total}
    return None


class AiUsageTracker:
    """
    Records and queries the AI token consumption of a project.

    The data is stored in a dedicated table 'ai_usage' inside the project
    database (data.qda). The table is created on demand the first time it is
    used, so this works with any database version and does not interfere with
    the regular schema migration.

    All database access opens its own short lived connection. This is required
    because the AI runs in background threads, and an sqlite connection can not
    be shared across threads.
    """

    def __init__(self, app):
        self.app = app
        # Marks the beginning of the current QualCoder session, used to show
        # how many tokens were consumed since the program was started.
        self.session_start = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")

    # database
    def _db_path(self):
        if self.app is None or not self.app.project_path:
            return None
        return os.path.join(self.app.project_path, 'data.qda')

    def _connect(self):
        db_path = self._db_path()
        if db_path is None or not os.path.exists(db_path):
            return None
        return sqlite3.connect(db_path)

    @staticmethod
    def _ensure_table(conn):
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS ai_usage ("
            "usageid integer primary key, "
            "date text, "
            "provider text, "
            "model text, "
            "task text, "
            "input_tokens integer, "
            "output_tokens integer, "
            "total_tokens integer, "
            "estimated integer)"
        )
        conn.commit()

    def ensure_table(self):
        """Public helper, makes sure the storage exists for the current project."""
        conn = self._connect()
        if conn is None:
            return
        try:
            self._ensure_table(conn)
        finally:
            conn.close()

    # helpers
    def _resolve_provider_model(self, llm):
        """Return (provider_name, model_name) for the call.
        The provider is the name of the AI profile selected in the settings,
        the model is read from the live llm object when possible (this keeps
        large and fast models apart)."""
        provider = ''
        model = ''
        try:
            idx = int(self.app.settings.get('ai_model_index', -1))
            if 0 <= idx < len(self.app.ai_models):
                profile = self.app.ai_models[idx]
                provider = profile.get('name', '')
                model = profile.get('large_model', '')
        except Exception:
            pass
        # Prefer the model name of the actual llm instance, if available
        for attr in ('model_name', 'model'):
            value = getattr(llm, attr, None)
            if isinstance(value, str) and value:
                model = value
                break
        return provider or _('Unknown provider'), model or _('Unknown model')

    def _estimate_tokens(self, llm, messages_in, text_out):
        """
        Estimate input and output tokens using the model tokenizer, with a
        character based fallback.
        """
        
        # Input
        input_tokens = 0
        try:
            if isinstance(messages_in, str):
                input_tokens = int(llm.get_num_tokens(messages_in))
            elif isinstance(messages_in, (list, tuple)):
                input_tokens = int(llm.get_num_tokens_from_messages(list(messages_in)))
            else:
                input_tokens = _estimate_text_tokens(messages_in)
        except Exception:
            if isinstance(messages_in, (list, tuple)):
                joined = ' '.join(str(getattr(m, 'content', m)) for m in messages_in)
                input_tokens = _estimate_text_tokens(joined)
            else:
                input_tokens = _estimate_text_tokens(messages_in)
        # Output
        output_tokens = 0
        try:
            output_tokens = int(llm.get_num_tokens(text_out)) if text_out else 0
        except Exception:
            output_tokens = _estimate_text_tokens(text_out)
        return input_tokens, output_tokens

    # record
    def record(self, llm, messages_in, text_out, task=TASK_OTHER, response=None):
        """
        Record one AI call.

        Args:
            llm: the LangChain chat model used for the call (large_llm/fast_llm).
            messages_in: the prompt sent to the model (list of messages or str).
            text_out: the textual answer returned by the model.
            task: one of the TASK_* constants, identifies the QualCoder feature.
            response: the LangChain message/chunk returned by the model, used to
                read the real token usage when the provider reports it.

        This method never raises: token tracking must not break an AI operation.
        """
        try:
            provider, model = self._resolve_provider_model(llm)
            usage = _extract_real_usage(response)
            if usage is not None:
                input_tokens = usage['input']
                output_tokens = usage['output']
                total_tokens = usage['total']
                estimated = 0
            else:
                input_tokens, output_tokens = self._estimate_tokens(llm, messages_in, text_out)
                total_tokens = input_tokens + output_tokens
                estimated = 1
            if total_tokens <= 0:
                return  # nothing meaningful to store
            now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
            conn = self._connect()
            if conn is None:
                return
            try:
                self._ensure_table(conn)
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO ai_usage (date, provider, model, task, input_tokens, "
                    "output_tokens, total_tokens, estimated) values (?,?,?,?,?,?,?,?)",
                    (now, provider, model, task, input_tokens, output_tokens, total_tokens, estimated)
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as e:
            logger.debug('AI usage tracking failed: ' + str(e))

    # queries
    def totals(self, since=None):
        """
        Return overall totals as a dict.
        If 'since' (an ISO datetime string) is given, only rows from that moment
        on are counted
        """
        
        empty = {'calls': 0, 'input': 0, 'output': 0, 'total': 0, 'estimated_calls': 0}
        conn = self._connect()
        if conn is None:
            return empty
        try:
            self._ensure_table(conn)
            cur = conn.cursor()
            sql = ("SELECT count(*), ifnull(sum(input_tokens),0), ifnull(sum(output_tokens),0), "
                   "ifnull(sum(total_tokens),0), ifnull(sum(estimated),0) FROM ai_usage")
            params = ()
            if since is not None:
                sql += " WHERE date >= ?"
                params = (since,)
            cur.execute(sql, params)
            row = cur.fetchone()
            if row is None:
                return empty
            return {'calls': row[0], 'input': row[1], 'output': row[2],
                    'total': row[3], 'estimated_calls': row[4]}
        finally:
            conn.close()

    def totals_by_model(self):
        """
        Return a list of dicts grouped by provider and model, newest first
        """
        
        conn = self._connect()
        if conn is None:
            return []
        try:
            self._ensure_table(conn)
            cur = conn.cursor()
            cur.execute(
                "SELECT provider, model, count(*), ifnull(sum(input_tokens),0), "
                "ifnull(sum(output_tokens),0), ifnull(sum(total_tokens),0), "
                "ifnull(sum(estimated),0), max(date) "
                "FROM ai_usage GROUP BY provider, model ORDER BY sum(total_tokens) DESC"
            )
            rows = cur.fetchall()
            keys = ('provider', 'model', 'calls', 'input', 'output', 'total', 'estimated_calls', 'last_used')
            return [dict(zip(keys, r)) for r in rows]
        finally:
            conn.close()

    def totals_by_task(self):
        """
        Return a list of dicts grouped by task.
        """
        conn = self._connect()
        if conn is None:
            return []
        try:
            self._ensure_table(conn)
            cur = conn.cursor()
            cur.execute(
                "SELECT task, count(*), ifnull(sum(input_tokens),0), "
                "ifnull(sum(output_tokens),0), ifnull(sum(total_tokens),0) "
                "FROM ai_usage GROUP BY task ORDER BY sum(total_tokens) DESC"
            )
            rows = cur.fetchall()
            keys = ('task', 'calls', 'input', 'output', 'total')
            return [dict(zip(keys, r)) for r in rows]
        finally:
            conn.close()

    def all_rows(self):
        """
        Return every recorded call (used for CSV export), newest first
        """
        
        conn = self._connect()
        if conn is None:
            return []
        try:
            self._ensure_table(conn)
            cur = conn.cursor()
            cur.execute(
                "SELECT date, provider, model, task, input_tokens, output_tokens, "
                "total_tokens, estimated FROM ai_usage ORDER BY date DESC, usageid DESC"
            )
            rows = cur.fetchall()
            keys = ('date', 'provider', 'model', 'task', 'input', 'output', 'total', 'estimated')
            return [dict(zip(keys, r)) for r in rows]
        finally:
            conn.close()

    def reset(self):
        """
        Delete all recorded usage for the current project
        """
        
        conn = self._connect()
        if conn is None:
            return
        try:
            self._ensure_table(conn)
            cur = conn.cursor()
            cur.execute("DELETE FROM ai_usage")
            conn.commit()
        finally:
            conn.close()

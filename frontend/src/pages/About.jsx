const RUN = `git clone https://github.com/Carlos28042003/agent-profilling.git
cd agent-profilling/backend
uv sync
ollama pull llama3.2:3b
ollama create llama3.2:3b-ctx8k -f configs/ollama/llama3.2-ctx8k.Modelfile
uv run agentic-ui        # this page + the live "Ask the agent" tab`;

export default function About() {
  return (
    <div className="card p-6 space-y-4 max-w-3xl leading-relaxed">
      <h3 className="font-semibold text-lg">What this project measures</h3>
      <p className="secondary">
        A ReAct agent answers a question in steps: it thinks, calls a tool (Wikipedia search and lookup, a calculator
        or Python), reads the result, and repeats. The model has no memory between steps, so every call re-sends the
        whole conversation so far. Most of each prompt is therefore text the model has already processed.
      </p>
      <p className="secondary">
        This project records, for every step, the time to first token, generation time, tool time, prompt and output
        tokens, and how much of the prompt is a repeated prefix. The traces are used to measure how much serving
        optimizations such as prefix caching help, for one agent and for many concurrent agents.
      </p>
      <h3 className="font-semibold text-lg">Run it yourself</h3>
      <pre className="p-4 rounded-lg text-xs mono overflow-x-auto" style={{ background: "var(--surface-2)" }}>{RUN}</pre>
    </div>
  );
}

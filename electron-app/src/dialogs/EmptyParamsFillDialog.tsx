import React, { useState } from "react";
import { X, Play } from "lucide-react";

type EmptyParamField = {
  nodeId: string;
  nodeTitle: string;
  paramKey: string;
  paramLabel: string;
  defaultValue: string;
};

interface EmptyParamsFillDialogProps {
  emptyFields: EmptyParamField[];
  onConfirm: (filledValues: Record<string, Record<string, string>>) => void;
  onCancel: () => void;
}

export const EmptyParamsFillDialog: React.FC<EmptyParamsFillDialogProps> = ({
  emptyFields,
  onConfirm,
  onCancel,
}) => {
  const [values, setValues] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {};
    emptyFields.forEach((field) => {
      initial[`${field.nodeId}:${field.paramKey}`] = field.defaultValue || "";
    });
    return initial;
  });

  const handleChange = (key: string, val: string) => {
    setValues((prev) => ({ ...prev, [key]: val }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const result: Record<string, Record<string, string>> = {};
    emptyFields.forEach((field) => {
      const val = values[`${field.nodeId}:${field.paramKey}`] || "";
      if (!result[field.nodeId]) {
        result[field.nodeId] = {};
      }
      result[field.nodeId][field.paramKey] = val;
    });
    onConfirm(result);
  };

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => e.target === e.currentTarget && onCancel()}
    >
      <form className="modal panel fill-dialog-modal" onSubmit={handleSubmit}>
        <div className="modal-head">
          <div>
            <div className="panel-kicker">PRE-LAUNCH CONFIGURATION</div>
            <h2>Заполнение незаполненных полей</h2>
            <span className="account-path">
              Введите значения один раз для массового старта сценария
            </span>
          </div>
          <button type="button" className="more-btn" onClick={onCancel}>
            <X size={17} />
          </button>
        </div>

        <p className="modal-copy">
          В вашем графе обнаружены пустые параметры. Пожалуйста, укажите нужные
          ссылки, юзернеймы или тексты:
        </p>

        <div
          className="fill-fields-scroll"
          style={{ maxHeight: "50vh", overflowY: "auto", paddingRight: "6px" }}
        >
          {emptyFields.map((field) => {
            const compositeKey = `${field.nodeId}:${field.paramKey}`;
            return (
              <div
                key={compositeKey}
                className="fill-field-group"
                style={{
                  marginBottom: "14px",
                  padding: "10px",
                  background: "#080e09",
                  borderRadius: "8px",
                  border: "1px solid var(--border)",
                }}
              >
                <div
                  style={{
                    fontSize: "11px",
                    color: "var(--green)",
                    fontWeight: "bold",
                    marginBottom: "4px",
                  }}
                >
                  Блок: {field.nodeTitle}
                </div>
                <label className="form-field" style={{ margin: 0 }}>
                  {field.paramLabel.toUpperCase()}
                  <input
                    type="text"
                    value={values[compositeKey] || ""}
                    onChange={(e) => handleChange(compositeKey, e.target.value)}
                    placeholder={`Введите ${field.paramLabel.toLowerCase()}...`}
                    style={{ marginTop: "6px" }}
                  />
                </label>
              </div>
            );
          })}
        </div>

        <div className="modal-footer">
          <button type="button" className="tool-btn" onClick={onCancel}>
            Отмена
          </button>
          <button className="primary-btn" type="submit">
            <Play size={15} /> Пропустить и Запустить
          </button>
        </div>
      </form>
    </div>
  );
};
